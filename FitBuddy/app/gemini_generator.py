"""
gemini_generator.py
--------------------
Responsible for generating the original 7-day workout plan using the
"workout" Gemini model (see gemini_client.py for model configuration).
"""

from app.gemini_client import WORKOUT_MODEL, call_gemini, plan_to_storage_json

WORKOUT_PROMPT_TEMPLATE = """You are FitBuddy, an expert certified personal fitness coach AI.

Create a personalized 7-day workout plan for the following person:
- Name: {name}
- Age: {age}
- Weight: {weight} kg
- Fitness Goal: {goal}
- Workout Intensity: {intensity}

Design the plan to genuinely suit this person's age, weight, goal and intensity
level (for example, include appropriate rest days for "Low" intensity, and
more sessions for "High" intensity). Keep exercises realistic and safe for a
general audience with no equipment beyond common gym/home basics.

Respond with ONLY valid JSON (no markdown fences, no commentary before or
after) using EXACTLY this schema:

{{
  "days": [
    {{
      "day": "Day 1",
      "focus": "short focus area, e.g. Full Body / Cardio / Rest",
      "warm_up": "short warm-up description",
      "exercises": "list of exercises as a single readable string, separated by commas or line breaks",
      "sets_reps": "sets, reps or duration for the exercises above",
      "rest": "rest interval guidance between sets/exercises",
      "cooldown": "short cooldown / recovery guidance"
    }}
  ]
}}

The "days" array must contain exactly 7 entries, one for each day of the week
(Day 1 through Day 7). If a day is a rest or active-recovery day, still fill
in every field (e.g. focus: "Rest / Active Recovery")."""


def generate_workout_gemini(name: str, age: int, weight: float, goal: str, intensity: str):
    """
    Calls Gemini to generate a 7-day workout plan.

    Returns a tuple: (storage_json, raw_text)
      - storage_json: JSON string ready to store in the database
      - raw_text: the raw text Gemini returned (useful for debugging/logging)
    """
    prompt = WORKOUT_PROMPT_TEMPLATE.format(
        name=name, age=age, weight=weight, goal=goal, intensity=intensity
    )
    raw_text = call_gemini(WORKOUT_MODEL, prompt, want_json=True, temperature=0.8)
    storage_json = plan_to_storage_json(raw_text)
    return storage_json, raw_text
