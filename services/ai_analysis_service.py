from openai import OpenAI
from backend.config import settings
import logging
import json

logger = logging.getLogger(__name__)

class AIAnalysisService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.AI_MODEL
    
    def analyze_post_content(self, post_text: str, customer_product: str = "") -> dict:
        """
        Uses AI to analyze the post content and extract:
        - Intent (problem, solution-seeking, discussion, promotion)
        - Topics/keywords
        - Relevance to customer's product
        """
        if not self.client:
            logger.warning("OpenAI not configured, skipping AI analysis")
            return {"intent": "unknown", "topics": [], "relevance_score": 50}
        
        prompt = f"""Analyze this LinkedIn post and return a JSON response:

Post: "{post_text}"
Customer Product/Service: "{customer_product or 'General B2B SaaS'}"

Return JSON with:
- intent: one of [problem, solution_seeking, discussion, success_story, promotion, question]
- topics: list of 3-5 main topics/keywords
- relevance_score: 0-100 how relevant to customer's product
- summary: one-line summary

Example: {{"intent": "problem", "topics": ["CRM", "sales automation"], "relevance_score": 85, "summary": "User seeking CRM recommendations"}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"AI post analysis failed: {str(e)}")
            return {"intent": "unknown", "topics": [], "relevance_score": 50, "summary": ""}
    
    def evaluate_profile(self, name: str, headline: str, comment_text: str, persona_definition: dict) -> dict:
        """
        AI-powered profile evaluation:
        - Classify as Individual or Company
        - Extract role, seniority, industry signals
        - Match against persona
        - Detect buying intent from comment
        """
        if not self.client:
            return self._fallback_evaluation(headline)
        
        prompt = f"""Evaluate this LinkedIn profile interaction:

Name: {name}
Headline: {headline}
Their Comment: "{comment_text}"

Target Persona:
- Industries: {persona_definition.get('industries', [])}
- Job Titles: {persona_definition.get('job_titles', [])}
- Seniority: {persona_definition.get('seniority', [])}

Return JSON with:
- profile_type: "individual" or "company"
- role_category: e.g., "decision_maker", "influencer", "end_user", "irrelevant"
- seniority_level: "C-level", "VP", "Director", "Manager", "IC", "Student"
- industry_match: true/false
- intent_from_comment: "high" (asking, seeking solution), "medium" (sharing opinion), "low" (general engagement)
- persona_fit_score: 0-100
- reasoning: brief explanation

Example: {{"profile_type": "individual", "role_category": "decision_maker", "seniority_level": "VP", "industry_match": true, "intent_from_comment": "high", "persona_fit_score": 92, "reasoning": "VP Sales in SaaS, actively seeking solutions"}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"AI profile evaluation failed: {str(e)}")
            return self._fallback_evaluation(headline)
    
    def _fallback_evaluation(self, headline: str) -> dict:
        """Simple rule-based fallback if AI fails"""
        seniority = "IC"
        if any(x in headline for x in ["CEO", "Founder", "President"]):
            seniority = "C-level"
        elif any(x in headline for x in ["VP", "Vice President"]):
            seniority = "VP"
        elif "Director" in headline:
            seniority = "Director"
        elif "Manager" in headline:
            seniority = "Manager"
        
        excluded = any(x in headline.lower() for x in ["student", "recruiter", "intern"])
        
        return {
            "profile_type": "company" if "Company" in headline or "Ltd" in headline else "individual",
            "role_category": "irrelevant" if excluded else "influencer",
            "seniority_level": seniority,
            "industry_match": False,
            "intent_from_comment": "medium",
            "persona_fit_score": 0 if excluded else 50,
            "reasoning": "Fallback evaluation (AI unavailable)"
        }

ai_analysis_service = AIAnalysisService()
