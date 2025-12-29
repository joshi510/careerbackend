import os
from typing import Dict, Optional, Tuple
import json


def get_gemini_client():
    """Get Gemini client using API key from environment variable"""
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None, "GEMINI_API_KEY environment variable is not set"
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        return model, None
    except ImportError:
        return None, "Google Generative AI SDK not installed. Install with: pip install google-generativeai"
    except Exception as e:
        error_msg = str(e)
        # Sanitize error message to avoid exposing secrets
        if "API key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Gemini API authentication failed"
        return None, f"Gemini client initialization error: {error_msg}"


def generate_interpretation(context: Dict) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Generate career interpretation using Gemini AI
    
    Args:
        context: Dictionary containing:
            - total_questions: int
            - correct_answers: int
            - percentage: float
            - readiness_band: str (High/Medium/Low)
            - category_scores: Optional[Dict] (optional)
    
    Returns:
        Tuple of (interpretation_dict, error_message)
        If successful: (dict, None)
        If failed: (None, error_message)
    """
    model, error = get_gemini_client()
    if error:
        return None, error
    
    if not model:
        return None, "Gemini client not available"
    
    # Build prompt
    total_questions = context.get("total_questions", 0)
    correct_answers = context.get("correct_answers", 0)
    percentage = context.get("percentage", 0.0)
    readiness_band = context.get("readiness_band", "Medium")
    category_scores = context.get("category_scores")
    
    category_info = ""
    if category_scores:
        category_info = "\nCategory Breakdown:\n"
        for cat, score in category_scores.items():
            category_info += f"- {cat}: {score}%\n"
    
    prompt = f"""You are a career guidance AI. Provide guidance only. No medical or psychological diagnosis.

ASSESSMENT RESULTS:
- Total Questions: {total_questions}
- Correct Answers: {correct_answers}
- Percentage Score: {percentage}%
- Readiness Band: {readiness_band}
{category_info}

TASK:
Generate a structured JSON response with the following exact structure:

{{
  "summary": "A 2-3 sentence overview of the assessment results focusing on career readiness",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["area for improvement 1", "area for improvement 2"],
  "career_clusters": ["cluster 1", "cluster 2", "cluster 3"],
  "risk_level": "LOW" or "MEDIUM" or "HIGH",
  "readiness_status": "READY" or "PARTIALLY READY" or "NOT READY",
  "action_plan": [
    "Step 1 for next 6 months",
    "Step 2 for 6-12 months",
    "Step 3 for 12-24 months"
  ]
}}

IMPORTANT:
- Return ONLY valid JSON, no markdown, no code blocks
- risk_level should be LOW if percentage >= 70, MEDIUM if 50-69, HIGH if < 50
- readiness_status should align with readiness_band
- Use positive, encouraging language throughout
- Focus on career development, not diagnosis

Return the JSON now:"""
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        interpretation = json.loads(response_text)
        
        # Validate required fields
        required_fields = ["summary", "strengths", "weaknesses", "career_clusters", 
                          "risk_level", "readiness_status", "action_plan"]
        for field in required_fields:
            if field not in interpretation:
                return None, f"Gemini response missing required field: {field}"
        
        return interpretation, None
    except json.JSONDecodeError as e:
        return None, f"Failed to parse Gemini JSON response: {str(e)}"
    except Exception as e:
        error_msg = str(e)
        # Sanitize error message
        if "API key" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Gemini API authentication failed"
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            error_msg = "Gemini API rate limit exceeded"
        return None, f"Gemini API error: {error_msg}"

