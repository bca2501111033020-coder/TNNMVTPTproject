"""
models.py
---------
SQLAlchemy ORM models for FitBuddy.

User          -> one row per registered user (identified by user_id)
WorkoutPlan   -> one row per generated plan, linked back to a User.
                 Stores both the original AI-generated plan and any
                 feedback-updated plan, plus the nutrition tip.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (same values as the deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    goal = Column(String(50), nullable=False)
    intensity = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    plans = relationship(
        "WorkoutPlan", back_populates="user", cascade="all, delete-orphan"
    )


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)

    # JSON-encoded text. Either structured JSON produced by Gemini
    # ({"days": [...]}) or a fallback {"raw_text": "..."} if parsing failed.
    original_plan = Column(Text, nullable=False)
    updated_plan = Column(Text, nullable=True)

    nutrition_tip = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="plans")
