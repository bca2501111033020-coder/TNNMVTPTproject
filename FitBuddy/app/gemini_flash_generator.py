"""
gemini_flash_generator.py
--------------------------
Responsible for generating a short nutrition/recovery tip using the
fast "tip" Gemini model (see gemini_client.py for model configuration).
"""

from app.gemini_client import TIP_MODEL, call_gemini

TIP_PROMPT_TEMPLATE = """You are a fitness nutrition assistant.

Give ONE short, practical nutrition and recovery tip (3-5 sentences,
plain text, no headings, no markdown, no bullet points) for someone
whose fitness goal is "{goal}".

Keep it encouraging, general-audience friendly, and NOT medical advice.
Do not diagnose or recommend supplements, medications, or extreme diets."""


def generate_nutrition_tip_with_flash(goal: str) -> str:
    """Calls the fast Gemini model to generate a concise nutrition/recovery tip."""
    prompt = TIP_PROMPT_TEMPLATE.format(goal=goal)
    tip = call_gemini(TIP_MODEL, prompt, want_json=False, temperature=0.6)
    return tip.strip()
