"""
schemas.py
----------
Pydantic models used to validate incoming form data before it is
processed by the routes. Keeps validation logic out of routes.py.
"""

import math
import re

from pydantic import BaseModel, ValidationError, field_validator

VALID_GOALS = {
    "Weight Loss",
    "Muscle Gain",
    "General Wellness",
    "Flexibility",
    "Strength",
    "Endurance",
}

VALID_INTENSITIES = {"Low", "Medium", "High"}

# Letters, digits, underscore, dot and hyphen only: safe inside a URL path
# such as /feedback/{user_id}.
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")

MAX_FEEDBACK_LENGTH = 1000


def first_error_message(exc: ValidationError) -> str:
    """Turn a Pydantic ValidationError into one short, user-friendly sentence."""
    err = exc.errors()[0]
    msg = err.get("msg", "Invalid value.")
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, "):]
    if err.get("type") == "value_error":
        return msg
    loc = err.get("loc") or ()
    field = str(loc[0]).replace("_", " ") if loc else "input"
    return f"{field}: {msg}"


class UserInput(BaseModel):
    name: str
    user_id: str
    age: int
    weight: float
    goal: str
    intensity: str

    @field_validator("name")
    @classmethod
    def name_valid(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("Name is required.")
        if len(v) > 100:
            raise ValueError("Name must be 100 characters or fewer.")
        return v

    @field_validator("user_id")
    @classmethod
    def user_id_valid(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("User ID is required.")
        if not USER_ID_PATTERN.match(v):
            raise ValueError(
                "User ID may only contain letters, numbers, '_', '-' and '.' (max 64 characters)."
            )
        return v

    @field_validator("age")
    @classmethod
    def age_reasonable(cls, v):
        if v < 10 or v > 100:
            raise ValueError("Age must be between 10 and 100.")
        return v

    @field_validator("weight")
    @classmethod
    def weight_positive(cls, v):
        if not math.isfinite(v) or v <= 0 or v > 400:
            raise ValueError("Weight must be a positive, realistic number (in kg).")
        return v

    @field_validator("goal")
    @classmethod
    def goal_valid(cls, v):
        if v not in VALID_GOALS:
            raise ValueError(f"Goal must be one of: {', '.join(sorted(VALID_GOALS))}")
        return v

    @field_validator("intensity")
    @classmethod
    def intensity_valid(cls, v):
        if v not in VALID_INTENSITIES:
            raise ValueError(f"Intensity must be one of: {', '.join(sorted(VALID_INTENSITIES))}")
        return v


class FeedbackRequest(BaseModel):
    user_id: str
    feedback: str

    @field_validator("user_id")
    @classmethod
    def user_id_not_empty(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("User ID is required.")
        return v

    @field_validator("feedback")
    @classmethod
    def feedback_valid(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("Feedback cannot be empty.")
        if len(v) > MAX_FEEDBACK_LENGTH:
            raise ValueError(f"Feedback must be {MAX_FEEDBACK_LENGTH} characters or fewer.")
        return v
