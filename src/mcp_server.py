import sys
import json
import os
import sqlite3
import pandas as pd
from src.profile_manager import ProfileManager
from src.engine import RecommendationEngine
from src.audit_engine import AdmissionsAuditEngine

def initialize_user_profile(province, score, rank, category, subjects, eyesight_color="Normal", english_score=0, city_preferences="", user_id="testuser", username="李华", db_path="data/lucid.db"):
    manager = ProfileManager(db_path=db_path)
    profile = {
        "user_id": user_id,
        "username": username,
        "province": province,
        "score": int(score),
        "rank": int(rank),
        "category": category,
        "subjects": subjects,
        "eyesight_color": eyesight_color,
        "english_score": int(english_score),
        "city_preferences": city_preferences
    }
    manager.save_profile(profile)
    return {"status": "success", "message": f"Successfully created/updated profile for '{user_id}'."}

def run_lucid_engine(user_id="testuser", db_path="data/lucid.db", chroma_db="data/chroma_db"):
    profile_manager = ProfileManager(db_path=db_path)
    profile = profile_manager.load_profile(user_id)
    if not profile:
        return {"status": "error", "message": f"Profile not found for user_id '{user_id}'. Run 'initialize_user_profile' first."}
        
    engine = RecommendationEngine(db_path=chroma_db)
    
    db_conn = sqlite3.connect(db_path)
    colleges_df = pd.read_sql_query("SELECT * FROM college_admissions", db_conn)
    db_conn.close()
    
    if colleges_df.empty:
        return {"status": "error", "message": "Admissions database is empty. Please ingest historical admissions data first."}

    if 'historical_ranks' not in colleges_df.columns:
        colleges_df['historical_ranks'] = colleges_df['min_rank'].apply(lambda x: [int(x), int(x * 1.02), int(x * 0.98)])
    if 'historical_lowest_rank' not in colleges_df.columns:
        colleges_df['historical_lowest_rank'] = colleges_df['min_rank']
    if 'school_name' not in colleges_df.columns:
        colleges_df['school_name'] = colleges_df['college_name']
    if 'school_level' not in colleges_df.columns:
        colleges_df['school_level'] = colleges_df['college_tags']

    # Step 1: Rough Sort
    rough_pool = engine.rough_sort(profile['rank'], colleges_df)
    
    # Step 2: Fine Sort
    preferences = {}
    if profile.get('city_preferences'):
        preferences['cities'] = [c.strip() for c in profile['city_preferences'].split(',') if c.strip()]
    
    fine_pool = engine.fine_sort(rough_pool, preferences)
    
    # Step 3: Probability Ranking with Audit
    ranked_pool = engine.probability_ranking(profile['rank'], fine_pool, user_profile=profile)
    
    return {"status": "success", "recommendations": ranked_pool.to_dict(orient='records')}

def run_rag_audit(user_id, candidate_list, db_path="data/lucid.db", chroma_db="data/chroma_db"):
    profile_manager = ProfileManager(db_path=db_path)
    profile = profile_manager.load_profile(user_id)
    if not profile:
        return {"status": "error", "message": f"Profile not found for user_id '{user_id}'."}
        
    audit_engine = AdmissionsAuditEngine(db_path=chroma_db)
    audited_results = []
    
    for item in candidate_list:
        college_name = item.get('college_name') or item.get('school_name')
        major_name = item.get('major_name') or "Unknown Major"
        if not college_name:
            continue
            
        res = audit_engine.audit_candidate(profile, college_name, major_name)
        audited_results.append({
            "college_name": college_name,
            "major_name": major_name,
            "is_excluded": res.get("is_excluded", False),
            "warning_level": res.get("warning_level", "green"),
            "reason": res.get("reason", "")
        })
        
    return {"status": "success", "audit_results": audited_results}

def handle_request(req):
    """Handles JSON-RPC request for MCP Protocol."""
    method = req.get("method")
    params = req.get("params", {})
    req_id = req.get("id")

    # Map GOOGLE_API_KEY to GEMINI_API_KEY
    if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" in os.environ:
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "lucid-mcp-server",
                    "version": "1.0.0"
                }
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "initialize_user_profile",
                        "description": "Initialize or update candidate profile inside user_profiles table.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "province": {"type": "string", "description": "Candidate state/province, e.g. Zhejiang"},
                                "score": {"type": "integer", "description": "Total exam score"},
                                "rank": {"type": "integer", "description": "All state ranking位次"},
                                "category": {"type": "string", "description": "Category (Physics/History)"},
                                "subjects": {"type": "string", "description": "Comma-separated subjects list, e.g., Physics,Chemistry,Biology"},
                                "eyesight_color": {"type": "string", "default": "Normal", "description": "Normal, Weak (色弱), or Blind (色盲)"},
                                "english_score": {"type": "integer", "default": 0, "description": "English score"},
                                "city_preferences": {"type": "string", "default": "", "description": "Comma-separated desired cities, e.g., Shanghai,Beijing"},
                                "user_id": {"type": "string", "default": "testuser", "description": "User unique ID"},
                                "username": {"type": "string", "default": "李华"}
                            },
                            "required": ["province", "score", "rank", "category", "subjects"]
                        }
                    },
                    {
                        "name": "run_lucid_engine",
                        "description": "Trigger the double funnel & Gaussian probability recommendations for the candidate.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string", "default": "testuser", "description": "User unique ID"}
                            }
                        }
                    },
                    {
                        "name": "run_rag_audit",
                        "description": "Run the RAG audit on a list of candidate colleges against candidate profile.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string", "description": "User unique ID"},
                                "candidate_list": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "college_name": {"type": "string"},
                                            "major_name": {"type": "string"}
                                        },
                                        "required": ["college_name"]
                                    }
                                }
                            },
                            "required": ["user_id", "candidate_list"]
                        }
                    }
                ]
            }
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "initialize_user_profile":
                res = initialize_user_profile(**arguments)
            elif tool_name == "run_lucid_engine":
                res = run_lucid_engine(**arguments)
            elif tool_name == "run_rag_audit":
                # Convert candidate_list if it comes inside arguments
                res = run_rag_audit(**arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {tool_name}"
                    }
                }
            
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res, ensure_ascii=False, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }
            
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }

def main():
    """Stdio-based JSON-RPC Model Context Protocol (MCP) Server Loop."""
    sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            req = json.loads(line.strip())
            res = handle_request(req)
            sys.stdout.write(json.dumps(res, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as e:
            # Silence error or output structured log to stderr
            print(f"MCP Loop error: {e}", file=sys.stderr)

if __name__ == '__main__':
    main()
