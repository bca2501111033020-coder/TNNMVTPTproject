"""
updated_plan.py
----------------
Responsible for revising an existing 7-day workout plan based on user
feedback, using the same "workout" Gemini model used for the original
plan (see gemini_client.py for model configuration).
"""

import json

from app.gemini_client import WORKOUT_MODEL, call_gemini, plan_to_storage_json

UPDATE_PROMPT_TEMPLATE = """You are FitBuddy, an expert certified personal fitness coach AI.

A user was previously given the following 7-day workout plan (as JSON):

{original_plan_json}

The user's details:
- Name: {name}
- Age: {age}
- Weight: {weight} kg
- Fitness Goal: {goal}
- Workout Intensity: {intensity}

The user has given this feedback about the plan:
"{feedback}"

Revise the plan to genuinely address the feedback (do not just repeat the
old plan or append the feedback text to it -- actually change the relevant
days/exercises/focus areas). Keep everything else about the plan sound and
appropriate for the user's details above.

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

The "days" array must contain exactly 7 entries (Day 1 through Day 7)."""


def update_workout_plan(original_plan_json: str, feedback: str, name: str, age: int,
                         weight: float, goal: str, intensity: str):
    """
    Calls Gemini to produce a revised 7-day plan based on the original plan
    and the user's feedback.

    Returns a tuple: (storage_json, raw_text)
    """
    # Pretty-print the original plan JSON so Gemini can read it clearly.
    try:
        pretty_original = json.dumps(json.loads(original_plan_json), indent=2)
    except (json.JSONDecodeError, TypeError):
        pretty_original = str(original_plan_json)

    prompt = UPDATE_PROMPT_TEMPLATE.format(
        original_plan_json=pretty_original,
        name=name,
        age=age,
        weight=weight,
        goal=goal,
        intensity=intensity,
        feedback=feedback,
    )
    raw_text = call_gemini(WORKOUT_MODEL, prompt, want_json=True, temperature=0.8)
    storage_json = plan_to_storage_json(raw_text)
    return storage_json, raw_text
