import argparse
import json
import sys
import os
import pandas as pd
from src.profile_manager import ProfileManager
from src.engine import RecommendationEngine
from src.audit_engine import AdmissionsAuditEngine

def cmd_initialize_user_profile(args):
    """
    Initializes and saves the user profile to SQLite database.
    """
    manager = ProfileManager(db_path=args.db)
    profile = {
        "user_id": args.user_id,
        "username": args.username,
        "province": args.province,
        "score": args.score,
        "rank": args.rank,
        "category": args.category,
        "subjects": args.subjects,
        "eyesight_color": args.eyesight_color,
        "english_score": args.english_score,
        "city_preferences": args.city_preferences
    }
    
    # Remove keys with None values
    profile = {k: v for k, v in cleaned_nulls(profile).items()}
    
    manager.save_profile(profile)
    print(json.dumps({"status": "success", "message": f"Successfully created/updated profile for '{args.user_id}'."}))

def cmd_load_profile(args):
    """Loads a user profile from SQLite database."""
    manager = ProfileManager(db_path=args.db)
    profile = manager.load_profile(args.user_id)
    if profile:
        print(json.dumps({"status": "success", "profile": profile}, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "message": f"Profile not found for user_id '{args.user_id}'."}), file=sys.stderr)
        sys.exit(1)

def cmd_run_lucid_engine(args):
    """
    Runs the double-funnel recommendation engine for a user.
    """
    profile_manager = ProfileManager(db_path=args.db)
    profile = profile_manager.load_profile(args.user_id)
    if not profile:
        print(json.dumps({"status": "error", "message": f"Profile not found for user_id '{args.user_id}'. Run 'initialize_user_profile' first."}), file=sys.stderr)
        sys.exit(1)
        
    engine = RecommendationEngine(db_path=args.chroma_db)
    
    # Load all available college admissions data from SQLite
    conn = profile_manager.db_path # Wait, connect to SQLite for admissions data
    import sqlite3
    db_conn = sqlite3.connect(args.db)
    
    # Read admissions data
    colleges_df = pd.read_sql_query("SELECT * FROM college_admissions", db_conn)
    db_conn.close()
    
    if colleges_df.empty:
        # Fallback or error
        print(json.dumps({"status": "error", "message": "Admissions database is empty. Please ingest historical admissions data first."}), file=sys.stderr)
        sys.exit(1)

    # Convert historical_ranks string representation to list of ints
    # Usually in DB it could be single min_rank or we can synthesize it.
    # In college_admissions table, we have 'min_rank'. Let's synthesize historical_ranks using a small variation or directly [min_rank].
    # To be compatible with RecommendationEngine expectations:
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
    
    # Step 2: Fine Sort based on user preferences
    # Build preferences from profile
    preferences = {}
    if profile.get('city_preferences'):
        preferences['cities'] = [c.strip() for c in profile['city_preferences'].split(',') if c.strip()]
    
    # We can also add other preferences if needed
    fine_pool = engine.fine_sort(rough_pool, preferences)
    
    # Step 3: Probability Ranking with Audit
    ranked_pool = engine.probability_ranking(profile['rank'], fine_pool, user_profile=profile)
    
    # Convert DataFrame to JSON records
    records = ranked_pool.to_dict(orient='records')
    print(json.dumps({"status": "success", "recommendations": records}, ensure_ascii=False, indent=2))

def cmd_run_rag_audit(args):
    """
    Runs the RAG-based regulatory audit on a custom list of candidate colleges.
    """
    profile_manager = ProfileManager(db_path=args.db)
    profile = profile_manager.load_profile(args.user_id)
    if not profile:
        print(json.dumps({"status": "error", "message": f"Profile not found for user_id '{args.user_id}'."}), file=sys.stderr)
        sys.exit(1)
        
    try:
        candidates = json.loads(args.candidate_list)
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"Invalid JSON candidate list: {e}"}), file=sys.stderr)
        sys.exit(1)

    audit_engine = AdmissionsAuditEngine(db_path=args.chroma_db)
    audited_results = []
    
    for item in candidates:
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
        
    print(json.dumps({"status": "success", "audit_results": audited_results}, ensure_ascii=False, indent=2))

def cleaned_nulls(d):
    return {k: v for k, v in d.items() if v is not None}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Lucid OpenClaw CLI & Tools Interface")
    parser.add_argument("--db", default="data/lucid.db", help="Path to SQLite database")
    parser.add_argument("--chroma-db", default="data/chroma_db", help="Path to ChromaDB storage")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Subcommand: initialize_user_profile
    init_parser = subparsers.add_parser("initialize_user_profile", help="Initialize or update candidate profile")
    init_parser.add_argument("--user-id", default="testuser", help="User unique identifier")
    init_parser.add_argument("--username", default="李华", help="User display name")
    init_parser.add_argument("--province", required=True, help="Province (e.g. Zhejiang)")
    init_parser.add_argument("--score", type=int, required=True, help="Total exam score")
    init_parser.add_argument("--rank", type=int, required=True, help="State ranking/rank")
    init_parser.add_argument("--category", required=True, help="Exam category (Physics/History)")
    init_parser.add_argument("--subjects", required=True, help="Comma-separated subjects (Physics,Chemistry,...)")
    init_parser.add_argument("--eyesight_color", default="Normal", help="Eyesight status (Normal, Weak, Blind)")
    init_parser.add_argument("--english_score", type=int, default=0, help="English score")
    init_parser.add_argument("--city_preferences", default="", help="Comma-separated city preferences")
    
    # Subcommand: load_profile
    load_parser = subparsers.add_parser("load_profile", help="Load candidate profile")
    load_parser.add_argument("--user-id", default="testuser", help="User unique identifier")

    # Subcommand: run_lucid_engine
    engine_parser = subparsers.add_parser("run_lucid_engine", help="Run recommendation engine pipeline")
    engine_parser.add_argument("--user-id", default="testuser", help="User unique identifier")
    
    # Subcommand: run_rag_audit
    audit_parser = subparsers.add_parser("run_rag_audit", help="Run RAG audit on a list of colleges")
    audit_parser.add_argument("--user-id", default="testuser", help="User unique identifier")
    audit_parser.add_argument("--candidate-list", required=True, help="JSON array of college candidate objects")
    
    args = parser.parse_args()
    
    # Configure environment if key is found
    # Ensure google API keys from OpenClaw can map down
    if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" in os.environ:
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]

    if args.command == "initialize_user_profile":
        cmd_initialize_user_profile(args)
    elif args.command == "load_profile":
        cmd_load_profile(args)
    elif args.command == "run_lucid_engine":
        cmd_run_lucid_engine(args)
    elif args.command == "run_rag_audit":
        cmd_run_rag_audit(args)
