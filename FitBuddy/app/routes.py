"""
routes.py
---------
Request handling and page rendering for FitBuddy.
Keeps Gemini calls and DB access delegated to their own modules -
this file just wires the HTTP layer together.
"""

from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, WorkoutPlan, utcnow
from app.schemas import UserInput, FeedbackRequest, VALID_GOALS, first_error_message
from app.gemini_client import GeminiConfigError, GeminiRequestError, load_plan_for_display
from app.gemini_generator import generate_workout_gemini
from app.gemini_flash_generator import generate_nutrition_tip_with_flash
from app.updated_plan import update_workout_plan

BASE_DIR = Path(__file__).resolve().parent.parent

router = APIRouter()
# Absolute path, so the app works no matter which folder the server is started from.
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

INTENSITIES = ["Low", "Medium", "High"]


def render_error(request: Request, message: str, status_code: int = 400):
    # NOTE: current Starlette signature is TemplateResponse(request, name, context).
    # The old (name, context) form makes the context dict be treated as the
    # template name, which raises "TypeError: unhashable type: 'dict'".
    return templates.TemplateResponse(
        request,
        "error.html",
        {"message": message},
        status_code=status_code,
    )


def _latest_plan(db: Session, user_id: str):
    return (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.created_at.desc(), WorkoutPlan.id.desc())
        .first()
    )


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "goals": sorted(VALID_GOALS),
            "intensities": INTENSITIES,
        },
    )


def _upsert_user(db: Session, data: UserInput) -> User:
    """Return the user with this user_id, creating or updating the row as needed."""
    db_user = db.query(User).filter(User.user_id == data.user_id).first()
    if db_user is None:
        db_user = User(
            user_id=data.user_id, name=data.name, age=data.age,
            weight=data.weight, goal=data.goal, intensity=data.intensity,
        )
        db.add(db_user)
    else:
        # Keep the profile up to date if they generate a new plan later.
        db_user.name = data.name
        db_user.age = data.age
        db_user.weight = data.weight
        db_user.goal = data.goal
        db_user.intensity = data.intensity
    db.flush()
    return db_user


def _save_new_plan(db: Session, data: UserInput, plan_json: str, nutrition_tip):
    """
    Save user + plan in ONE transaction. If two requests create the same
    user_id at the same moment, the loser hits the unique constraint; it is
    rolled back and retried once as an update of the existing user.
    """
    last_error = None
    for _ in range(2):
        try:
            db_user = _upsert_user(db, data)
            db_plan = WorkoutPlan(
                user_id=db_user.user_id,
                original_plan=plan_json,
                updated_plan=None,
                nutrition_tip=nutrition_tip,
                feedback=None,
            )
            db.add(db_plan)
            db.commit()
            db.refresh(db_user)
            db.refresh(db_plan)
            return db_user, db_plan
        except IntegrityError as exc:
            db.rollback()
            last_error = exc
    raise last_error


@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout(
    request: Request,
    name: str = Form(...),
    user_id: str = Form(...),
    # Received as text on purpose: Pydantic converts and validates them, so a bad
    # value like "abc" gives a friendly error page instead of a raw 422 JSON reply.
    age: str = Form(...),
    weight: str = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
    db: Session = Depends(get_db),
):
    # ---- Validate input ----
    try:
        data = UserInput(
            name=name, user_id=user_id, age=age, weight=weight,
            goal=goal, intensity=intensity,
        )
    except ValidationError as exc:
        return render_error(request, f"Invalid input: {first_error_message(exc)}")

    # ---- Call Gemini BEFORE touching the database, so a failed AI call never
    #      leaves a half-created user or silently changes an existing profile. ----
    try:
        plan_json, _raw = generate_workout_gemini(
            data.name, data.age, data.weight, data.goal, data.intensity
        )
    except GeminiConfigError as exc:
        return render_error(request, str(exc), status_code=500)
    except GeminiRequestError as exc:
        return render_error(
            request,
            "FitBuddy could not reach the AI service right now. "
            "Please check your internet connection / API key and try again. "
            f"(Details: {exc})",
            status_code=502,
        )

    # The nutrition tip is a bonus: if only it fails, still deliver the plan.
    try:
        nutrition_tip = generate_nutrition_tip_with_flash(data.goal)
    except GeminiConfigError as exc:
        return render_error(request, str(exc), status_code=500)
    except GeminiRequestError:
        nutrition_tip = None

    # ---- Save to database ----
    try:
        db_user, db_plan = _save_new_plan(db, data, plan_json, nutrition_tip)
    except SQLAlchemyError:
        db.rollback()
        return render_error(
            request, "FitBuddy could not save your plan to the database. Please try again.",
            status_code=500,
        )

    return _render_result(request, db_user, db_plan)


def _render_result(request: Request, db_user: User, db_plan: WorkoutPlan, just_updated: bool = False):
    active_plan_json = db_plan.updated_plan if db_plan.updated_plan else db_plan.original_plan
    display_plan = load_plan_for_display(active_plan_json)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "user": db_user,
            "plan": db_plan,
            "display_plan": display_plan,
            "is_updated": bool(db_plan.updated_plan),
            "just_updated": just_updated,
        },
    )


@router.get("/feedback/{user_id}", response_class=HTMLResponse)
def feedback_page(request: Request, user_id: str, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.user_id == user_id).first()
    if db_user is None:
        return render_error(request, f"No user found with User ID '{user_id}'.", status_code=404)

    if _latest_plan(db, user_id) is None:
        return render_error(request, "This user does not have a generated plan yet.", status_code=404)

    return templates.TemplateResponse(request, "feedback.html", {"user": db_user})


@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback(
    request: Request,
    user_id: str = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    # ---- Validate input ----
    try:
        data = FeedbackRequest(user_id=user_id, feedback=feedback)
    except ValidationError as exc:
        return render_error(request, f"Invalid input: {first_error_message(exc)}")

    db_user = db.query(User).filter(User.user_id == data.user_id).first()
    if db_user is None:
        return render_error(request, f"No user found with User ID '{data.user_id}'.", status_code=404)

    db_plan = _latest_plan(db, data.user_id)
    if db_plan is None:
        return render_error(request, "No existing workout plan found for this user. Please generate a plan first.", status_code=404)

    # ---- Call Gemini to revise the plan ----
    try:
        updated_json, _raw = update_workout_plan(
            db_plan.original_plan, data.feedback,
            db_user.name, db_user.age, db_user.weight, db_user.goal, db_user.intensity,
        )
    except GeminiConfigError as exc:
        return render_error(request, str(exc), status_code=500)
    except GeminiRequestError as exc:
        return render_error(
            request,
            "FitBuddy could not reach the AI service while updating your plan. "
            f"Please try again. (Details: {exc})",
            status_code=502,
        )

    # ---- Save the update (never overwrite the original plan) ----
    try:
        db_plan.updated_plan = updated_json
        db_plan.feedback = data.feedback
        db_plan.updated_at = utcnow()
        db.commit()
        db.refresh(db_plan)
    except SQLAlchemyError:
        db.rollback()
        return render_error(
            request, "FitBuddy could not save your updated plan. Please try again.",
            status_code=500,
        )

    return _render_result(request, db_user, db_plan, just_updated=True)


@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request, q: str = "", db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    plans_by_user = {}
    for plan in db.query(WorkoutPlan).order_by(WorkoutPlan.created_at.desc(), WorkoutPlan.id.desc()).all():
        plans_by_user.setdefault(plan.user_id, []).append(plan)

    search = (q or "").strip().lower()
    rows = []
    for u in users:
        if search and search not in u.user_id.lower() and search not in u.name.lower():
            continue
        user_plans = plans_by_user.get(u.user_id, [])
        if not user_plans:
            # A user without any plan is still listed instead of silently disappearing.
            rows.append({"user": u, "plan": None, "original_display": None, "updated_display": None})
            continue
        for plan in user_plans:
            rows.append({
                "user": u,
                "plan": plan,
                "original_display": load_plan_for_display(plan.original_plan),
                "updated_display": load_plan_for_display(plan.updated_plan) if plan.updated_plan else None,
            })

    total_users = len(users)
    all_plans = [p for plist in plans_by_user.values() for p in plist]
    total_plans = len(all_plans)
    total_updated = sum(1 for p in all_plans if p.updated_plan)
    goal_distribution = Counter(u.goal for u in users)

    return templates.TemplateResponse(
        request,
        "all_users.html",
        {
            "rows": rows,
            "search": q,
            "total_users": total_users,
            "total_plans": total_plans,
            "total_updated": total_updated,
            "goal_distribution": dict(goal_distribution),
        },
    )
