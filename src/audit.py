import json
import os
import chromadb
import google.generativeai as genai

class AutomatedAudit:
    def __init__(self, db_path='data/chroma_db'):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(name="college_regulations")
        
        api_key = os.environ.get("GEMINI_API_KEY", "mock_api_key")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def retrieve_regulations(self, college_name: str) -> str:
        """
        Retrieves relevant admission regulations for the given college from ChromaDB.
        """
        try:
            results = self.collection.query(
                query_texts=[college_name],
                n_results=3,
                where={"college_name": college_name}
            )
            documents = results.get('documents', [[]])[0]
            return "\n".join(documents)
        except Exception as e:
            print(f"Error retrieving from Chroma: {e}")
            return ""

    def audit_major(self, user_profile: dict, college_name: str, major_name: str) -> dict:
        """
        Uses Gemini to check if the user profile violates any regulations for the major.
        """
        context = self.retrieve_regulations(college_name)
        if not context:
            return {"status": "Safe", "reason": "No specific regulations found or retrieved."}
            
        prompt = f"""
        User Profile:
        English Score: {user_profile.get('english_score', 'N/A')}
        Eyesight: {user_profile.get('eyesight_color', 'Normal')}
        
        College Regulations Context for {college_name}:
        {context}
        
        Is the user eligible for {major_name}? 
        Analyze restrictions like English score limits or color blindness/weakness.
        Return JSON with "status" ("Safe", "High Risk", "Rejected") and "reason".
        """
        
        # If API key is not present, we will simulate the check based on simple heuristics
        if os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_API_KEY") != "mock_api_key":
            try:
                response = self.model.generate_content(prompt)
                # Parse JSON from response
                # For robust implementation we should handle potential parsing errors
                result_text = response.text.strip()
                if result_text.startswith("```json"):
                    result_text = result_text[7:-3]
                return json.loads(result_text)
            except Exception as e:
                print(f"LLM Audit failed: {e}")
        
        # Simulated heuristic fallback
        reason = "All clear."
        status = "Safe"
        if "色盲" in context or "色弱" in context:
            if user_profile.get('eyesight_color') in ['Weak', 'Blind']:
                status = "Rejected"
                reason = "Major restricts color weakness/blindness based on regulations."
        
        if "英语" in context and "110" in context:
            if user_profile.get('english_score', 0) < 110:
                status = "High Risk"
                reason = "English score is below the mentioned threshold of 110."

        return {"status": status, "reason": reason}

    def generate_feishu_card(self, recommendations: list, user_profile: dict) -> dict:
        """
        Generates a Feishu interactive rich-text card highlighting risky/rejected majors.
        """
        elements = []
        for rec in recommendations:
            audit_result = self.audit_major(user_profile, rec['college_name'], rec['major_name'])
            status = audit_result['status']
            
            color = "green"
            if status == "Rejected":
                color = "red"
            elif status == "High Risk":
                color = "orange"
                
            tag = f"<font color='{color}'>[{status}]</font>"
            
            element = {
                "tag": "div",
                "text": {
                    "content": f"**{rec['college_name']}** - {rec['major_name']} {tag}\nProbability: {rec['probability']}%\nAudit Note: {audit_result['reason']}",
                    "tag": "lark_md"
                }
            }
            elements.append(element)
            elements.append({"tag": "hr"})
            
        # Remove the last hr
        if elements:
            elements.pop()
            
        card = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": "Lucid 志愿推荐与风控排雷报告 🚀"
                    },
                    "template": "blue"
                },
                "elements": elements
            }
        }
        return card

if __name__ == "__main__":
    audit = AutomatedAudit()
    
    sample_recs = [
        {"college_name": "Peking University", "major_name": "Computer Science", "probability": 95},
        {"college_name": "Tsinghua University", "major_name": "Art", "probability": 80}
    ]
    user_prof = {"english_score": 100, "eyesight_color": "Weak"}
    
    card_json = audit.generate_feishu_card(sample_recs, user_prof)
    print(json.dumps(card_json, ensure_ascii=False, indent=2))
