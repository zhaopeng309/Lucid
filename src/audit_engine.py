import json
import os
import chromadb
import google.generativeai as genai
from typing import Dict, Any

class AdmissionsAuditEngine:
    def __init__(self, db_path: str = 'data/chroma_db'):
        self.db_path = db_path
        if self.db_path == ":memory:":
            self.client = chromadb.EphemeralClient()
        else:
            self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(name="college_regulations")
        
        api_key = os.environ.get("GEMINI_API_KEY", "mock_api_key")
        genai.configure(api_key=api_key)
        # Using gemini-1.5-flash as the standard fast and reliable model
        self.model = genai.GenerativeModel('models/gemini-1.5-flash')

    def retrieve_regulations(self, college_name: str) -> str:
        """
        Retrieves relevant admission regulations for the given college from ChromaDB.
        """
        try:
            results = self.collection.query(
                query_texts=[college_name],
                n_results=5,  # Fetch up to 5 chunks for broader context
                where={"college_name": college_name}
            )
            documents = results.get('documents', [[]])[0]
            return "\n".join(documents)
        except Exception as e:
            print(f"Error retrieving from Chroma: {e}")
            return ""

    def audit_candidate(self, user_profile: dict, college_name: str, major_name: str) -> Dict[str, Any]:
        """
        Audits a candidate's profile against a college's regulations for a specific major.
        Returns a dict: {is_excluded: bool, warning_level: 'red'|'yellow'|'green', reason: str}
        """
        context = self.retrieve_regulations(college_name)
        if not context:
            return {
                "is_excluded": False,
                "warning_level": "green",
                "reason": "No specific regulations found for this college."
            }

        # Try using Gemini model if API key is real and configured
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key and api_key != "mock_api_key" and api_key != "":
            try:
                prompt = self._build_audit_prompt(user_profile, college_name, major_name, context)
                response = self.model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                result_text = response.text.strip()
                # strip markdown json blocks if present
                if result_text.startswith("```json"):
                    result_text = result_text[7:-3].strip()
                elif result_text.startswith("```"):
                    result_text = result_text[3:-3].strip()
                
                parsed_res = json.loads(result_text)
                return {
                    "is_excluded": bool(parsed_res.get("is_excluded", False)),
                    "warning_level": parsed_res.get("warning_level", "green"),
                    "reason": parsed_res.get("reason", "All clear.")
                }
            except Exception as e:
                print(f"Gemini Audit failed, falling back to heuristics. Error: {e}")

        # Heuristic fallback if Gemini is not available or fails
        return self._heuristic_audit(user_profile, college_name, major_name, context)

    def _build_audit_prompt(self, user_profile: dict, college_name: str, major_name: str, context: str) -> str:
        return f"""
You are an expert Admissions Audit Engine for Chinese college admissions (Lucid system).
Analyze whether the candidate's profile violates any regulations for enrolling in a specific major.

Candidate Profile:
- Name: {user_profile.get('username', 'Student')}
- Province: {user_profile.get('province', 'N/A')}
- Exam Category: {user_profile.get('category', 'N/A')}
- Exam Subjects: {user_profile.get('subjects', 'N/A')}
- Eyesight/Color Vision: {user_profile.get('eyesight_color', 'Normal')}
- English/Foreign Language Score: {user_profile.get('english_score', 0)}

Target College & Major:
- College: {college_name}
- Major: {major_name}

Official Admission Regulations Context for {college_name}:
{context}

Please conduct a careful audit across three categories:
1. Eyesight (Color Weakness/Blindness restrictions like "色盲", "色弱" limits for specific majors).
2. Single-subject scores (e.g., minimum English score like "英语单科成绩不低于110分" or similar).
3. Subjects Combination (e.g., whether the candidate's subjects combo meets the major's elective subject requirements, like "限考物理", "物理和化学" etc.).

Response MUST be a valid JSON object with EXACTLY the following structure:
{{
  "is_excluded": true or false,
  "warning_level": "red" or "yellow" or "green",
  "reason": "Clear explanation of audit results and any issues found"
}}

Rules for keys:
- "is_excluded": true if candidate violates a hard regulation and is definitely disqualified (red warning). false otherwise.
- "warning_level": 
  - "red" for definite disqualification / hard red lines.
  - "yellow" for high risk, borderline scores, or recommended warnings.
  - "green" for fully matching regulations.
- "reason": Detailed explanation in Chinese (as it's for Chinese高考).
"""

    def _heuristic_audit(self, user_profile: dict, college_name: str, major_name: str, context: str) -> Dict[str, Any]:
        """
        Heuristic fallback to audit the candidate profile offline using string matching.
        """
        is_excluded = False
        warning_level = "green"
        reasons = []

        # 1. Eyesight check
        eyesight = user_profile.get('eyesight_color', 'Normal')
        if eyesight != 'Normal':
            # Check for color weakness / blindness restrictions
            if "色弱" in context or "色盲" in context:
                # If candidate is Blind (色盲) or Weak (色弱)
                if eyesight == "Weak" and ("色弱" in context or "限招色弱" in context or "不招色弱" in context or "色盲" in context):
                    is_excluded = True
                    warning_level = "red"
                    reasons.append(f"该校章程存在视力/色觉限制，考生有【色弱】情况，可能被限制报考【{major_name}】专业。")
                elif eyesight == "Blind" and ("色盲" in context or "限招色盲" in context or "不招色盲" in context):
                    is_excluded = True
                    warning_level = "red"
                    reasons.append(f"该校章程存在视力/色觉限制，考生有【色盲】情况，可能被限制报考【{major_name}】专业。")

        # 2. English / Single-subject score check
        english_score = user_profile.get('english_score', 0)
        # Look for English score thresholds in text, typically "110", "115", "120"
        for thresh in [110, 115, 120, 100, 90]:
            if f"英语" in context and str(thresh) in context:
                if english_score < thresh:
                    is_excluded = True
                    warning_level = "red"
                    reasons.append(f"该校章程要求英语单科成绩不低于 {thresh} 分，考生当前英语成绩为 {english_score} 分，不符合要求。")
                    break

        # 3. Subject combo check
        subjects_str = user_profile.get('subjects', '')
        # Convert user subjects to lowercase set/list for uniform checking
        user_subs = [s.strip().lower() for s in subjects_str.split(',') if s.strip()]
        
        # Check if context contains subject requirements
        # e.g., "限考物理", "须选考物理", "必选物理", "物理和化学"
        if "物理" in context or "限考物理" in context or "必选物理" in context:
            # Check if physics or physical is in user subjects
            has_physics = any("physics" in s or "物理" in s for s in user_subs)
            if not has_physics and user_profile.get('category') != 'Physics':
                is_excluded = True
                warning_level = "red"
                reasons.append(f"报考【{major_name}】专业要求选考物理，考生未选择物理。")

        if "化学" in context or "限考化学" in context or "必选化学" in context:
            has_chem = any("chemistry" in s or "化学" in s for s in user_subs)
            if not has_chem:
                is_excluded = True
                warning_level = "red"
                reasons.append(f"报考【{major_name}】专业要求选考化学，考生未选择化学。")

        if is_excluded:
            reason = "；".join(reasons)
        else:
            reason = "未发现硬性规章限制，符合报考条件。"

        return {
            "is_excluded": is_excluded,
            "warning_level": warning_level,
            "reason": reason
        }
