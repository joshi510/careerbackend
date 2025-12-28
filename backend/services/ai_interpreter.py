from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import json
from models import Score, Career, InterpretedResult, TestAttempt
from config import settings


def get_ai_client():
    """Get AI client based on configuration"""
    try:
        import openai
        client = openai.OpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_API_BASE if settings.AI_API_BASE else None
        )
        return client
    except ImportError:
        raise ImportError("OpenAI library not installed. Install with: pip install openai")


def format_scores_for_ai(scores: List[Score]) -> str:
    """
    Format scores for AI interpretation without exposing raw values.
    Returns relative strength descriptions.
    """
    if not scores:
        return "No assessment scores available."
    
    # Sort by score value to identify relative strengths
    sorted_scores = sorted(scores, key=lambda x: x.score_value, reverse=True)
    
    # Categorize into relative strengths
    top_third = len(sorted_scores) // 3
    middle_third = top_third * 2
    
    strengths = []
    moderate = []
    developing = []
    
    for idx, score in enumerate(sorted_scores):
        dimension = score.dimension.replace("_", " ").title()
        if idx < top_third:
            strengths.append(dimension)
        elif idx < middle_third:
            moderate.append(dimension)
        else:
            developing.append(dimension)
    
    description = "Assessment Results:\n"
    if strengths:
        description += f"Strong areas: {', '.join(strengths)}\n"
    if moderate:
        description += f"Moderate areas: {', '.join(moderate)}\n"
    if developing:
        description += f"Areas for growth: {', '.join(developing)}\n"
    
    return description


def format_careers_for_ai(careers: List[Career]) -> str:
    """Format career recommendations for AI interpretation"""
    if not careers:
        return "No career recommendations available."
    
    career_list = []
    for career in sorted(careers, key=lambda x: x.order_index):
        match_desc = "high match" if career.match_score and career.match_score >= 70 else "moderate match" if career.match_score and career.match_score >= 50 else "exploratory option"
        career_list.append(f"- {career.career_name} ({career.category}): {career.description} - {match_desc}")
    
    return "Career Recommendations:\n" + "\n".join(career_list)


def generate_interpretation_prompt(scores_text: str, careers_text: str) -> str:
    """Generate prompt for AI interpretation"""
    return f"""You are a career guidance assistant helping to interpret psychometric assessment results. Your role is to provide supportive, encouraging explanations and actionable guidance.

IMPORTANT GUIDELINES:
- You are an ASSISTANT only - careers have already been determined by the system
- Do NOT diagnose, label, or use clinical/medical language
- Do NOT suggest the person has any conditions or disorders
- Focus on strengths, potential, and growth opportunities
- Use encouraging, positive language
- Provide practical, actionable advice

ASSESSMENT DATA:
{scores_text}

{careers_text}

TASK:
Generate a comprehensive interpretation that includes:

1. OVERALL INTERPRETATION (2-3 paragraphs):
   - Explain what the assessment reveals about the person's profile
   - Frame results positively, focusing on strengths and potential
   - Avoid diagnostic language or labels

2. KEY STRENGTHS (3-5 bullet points):
   - Highlight the person's strongest areas
   - Explain how these strengths can be valuable
   - Use positive, empowering language

3. GROWTH OPPORTUNITIES (3-5 bullet points):
   - Identify areas with potential for development
   - Frame as opportunities, not deficiencies
   - Suggest how these can be developed

4. CAREER FIT EXPLANATION (2-3 paragraphs):
   - Explain why the recommended careers align with their profile
   - Discuss how their strengths relate to each career
   - Be encouraging about career possibilities

5. 12-24 MONTH ACTION PLAN:
   - Provide a structured, realistic action plan
   - Include specific, actionable steps
   - Organize by timeframes (0-6 months, 6-12 months, 12-24 months)
   - Focus on skill development, exploration, and preparation

Format your response as JSON with these keys:
{{
  "interpretation_text": "Overall interpretation...",
  "strengths": "Bullet point 1\\nBullet point 2\\n...",
  "areas_for_improvement": "Opportunity 1\\nOpportunity 2\\n...",
  "action_plan": "0-6 months:\\n- Step 1\\n- Step 2\\n\\n6-12 months:\\n- Step 1\\n\\n12-24 months:\\n- Step 1"
}}""".replace("{CAREERS_TEXT}", careers_text)


def generate_ai_interpretation(db: Session, test_attempt_id: int) -> Dict:
    """
    Generate AI interpretation for test results.
    Returns interpretation data dictionary.
    """
    if not settings.AI_API_KEY:
        # Fallback interpretation if AI is not configured
        return {
            "interpretation_text": "Assessment completed. Please consult with a career counsellor for detailed interpretation.\n\nAction Plan:\n0-6 months: Review career recommendations\n6-12 months: Explore career options\n12-24 months: Take steps toward your chosen path",
            "strengths": "Review your assessment results to identify your key strengths.",
            "areas_for_improvement": "Consider areas where you'd like to grow and develop."
        }
    
    try:
        # Get test attempt
        test_attempt = db.query(TestAttempt).filter(TestAttempt.id == test_attempt_id).first()
        if not test_attempt:
            raise ValueError("Test attempt not found")
        
        # Get scores
        scores = db.query(Score).filter(Score.test_attempt_id == test_attempt_id).all()
        if not scores:
            raise ValueError("No scores found for test attempt")
        
        # Get career recommendations
        interpreted_result = db.query(InterpretedResult).filter(
            InterpretedResult.test_attempt_id == test_attempt_id
        ).first()
        
        careers = []
        if interpreted_result:
            careers = db.query(Career).filter(
                Career.interpreted_result_id == interpreted_result.id
            ).order_by(Career.order_index).all()
        
        # Format data for AI
        scores_text = format_scores_for_ai(scores)
        careers_text = format_careers_for_ai(careers)
        
        # Generate prompt
        prompt = generate_interpretation_prompt(scores_text, careers_text)
        
        # Call AI
        client = get_ai_client()
        response = client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a supportive career guidance assistant. Provide encouraging, practical guidance without using diagnostic or clinical language."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse response
        ai_content = response.choices[0].message.content.strip()
        
        # Try to parse as JSON, fallback to plain text
        try:
            interpretation_data = json.loads(ai_content)
            # Include action plan in interpretation text
            if "action_plan" in interpretation_data:
                interpretation_data["interpretation_text"] += "\n\n" + interpretation_data["action_plan"]
        except json.JSONDecodeError:
            # If not JSON, create structured response from text
            interpretation_data = {
                "interpretation_text": ai_content,
                "strengths": "Review your assessment results to identify your key strengths.",
                "areas_for_improvement": "Consider areas where you'd like to grow and develop."
            }
        
        return interpretation_data
        
    except Exception as e:
        # Fallback on error
        return {
            "interpretation_text": f"Assessment interpretation is being prepared. Error: {str(e)}",
            "strengths": "Your assessment results show various strengths across different dimensions.",
            "areas_for_improvement": "There are opportunities for growth in several areas."
        }


def store_ai_interpretation(db: Session, test_attempt_id: int) -> InterpretedResult:
    """
    Generate and store AI interpretation for test results.
    Returns the InterpretedResult object.
    """
    # Generate interpretation
    interpretation_data = generate_ai_interpretation(db, test_attempt_id)
    
    # Get or create interpreted result
    interpreted_result = db.query(InterpretedResult).filter(
        InterpretedResult.test_attempt_id == test_attempt_id
    ).first()
    
    if not interpreted_result:
        interpreted_result = InterpretedResult(
            test_attempt_id=test_attempt_id,
            interpretation_text=interpretation_data.get("interpretation_text", ""),
            strengths=interpretation_data.get("strengths"),
            areas_for_improvement=interpretation_data.get("areas_for_improvement"),
            is_ai_generated=True
        )
        db.add(interpreted_result)
    else:
        # Update existing interpretation
        interpreted_result.interpretation_text = interpretation_data.get("interpretation_text", interpreted_result.interpretation_text)
        interpreted_result.strengths = interpretation_data.get("strengths", interpreted_result.strengths)
        interpreted_result.areas_for_improvement = interpretation_data.get("areas_for_improvement", interpreted_result.areas_for_improvement)
        interpreted_result.is_ai_generated = True
    
    db.commit()
    db.refresh(interpreted_result)
    
    return interpreted_result

