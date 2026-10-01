"""
gemini_client.py
-----------------
Centralized Gemini service layer.

Every module that needs to talk to Gemini (gemini_generator.py,
gemini_flash_generator.py, updated_plan.py) goes through this file.
API-key handling, client creation, model configuration, error mapping and
JSON parsing all live in ONE place.

Configuration (all read from the .env file):

    GOOGLE_API_KEY         -> your Gemini API key (required)
    GEMINI_WORKOUT_MODEL   -> model for the 7-day plan and feedback revisions
    GEMINI_TIP_MODEL       -> model for the short nutrition/recovery tip
    GEMINI_FALLBACK_MODELS -> comma-separated models tried automatically if the
                              configured model answers "404 / no longer available"

Google retires and restricts model names regularly (for example, the Gemini 1.5
models are gone and the 2.5 models are now limited to accounts that already
used them), so the fallback list lets the app keep working without code edits.
"""

import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent

# Load <project>/.env explicitly so it works no matter which directory the
# server is started from. Real environment variables are NOT overridden.
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("fitbuddy.gemini")

# Stable Gemini 3.x models (as listed on ai.google.dev). All configurable via .env.
DEFAULT_WORKOUT_MODEL = "gemini-2.5-flash"
DEFAULT_TIP_MODEL = "gemini-2.5-flash"
DEFAULT_FALLBACK_MODELS = "gemini-2.5-flash"

WORKOUT_MODEL = os.getenv("GEMINI_WORKOUT_MODEL", DEFAULT_WORKOUT_MODEL).strip() or DEFAULT_WORKOUT_MODEL
TIP_MODEL = os.getenv("GEMINI_TIP_MODEL", DEFAULT_TIP_MODEL).strip() or DEFAULT_TIP_MODEL
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS).split(",")
    if m.strip()
]

PLAN_FIELDS = ("day", "focus", "warm_up", "exercises", "sets_reps", "rest", "cooldown")

_client = None
_client_key = None


class GeminiConfigError(Exception):
    """Raised when the Gemini API key is missing or rejected."""


class GeminiRequestError(Exception):
    """Raised when a call to the Gemini API fails (network, quota, timeout, etc.)."""


# --------------------------------------------------------------------------
# Client / configuration
# --------------------------------------------------------------------------
def _get_api_key() -> str:
    """Read the API key at call time. The .env placeholder counts as 'not set'."""
    key = os.getenv("GOOGLE_API_KEY", "").strip().strip('"').strip("'")
    if not key or key.lower().startswith("your_"):
        return ""
    return key


def get_client() -> "genai.Client":
    """Return a cached Gemini client, creating it on first use."""
    global _client, _client_key
    key = _get_api_key()
    if not key:
        raise GeminiConfigError(
            "GOOGLE_API_KEY is not set. Add your real Gemini API key to the .env file "
            "(see .env.example) and restart the server."
        )
    if _client is None or _client_key != key:
        _client = genai.Client(api_key=key)
        _client_key = key
    return _client


# --------------------------------------------------------------------------
# Calling Gemini
# --------------------------------------------------------------------------
def _model_candidates(primary: str):
    """The configured model first, then fallbacks, without duplicates."""
    ordered = []
    for m in [primary] + FALLBACK_MODELS:
        if m and m not in ordered:
            ordered.append(m)
    return ordered


def _status_code(exc: Exception):
    code = getattr(exc, "code", None)
    return code if isinstance(code, int) else None


def _is_model_unavailable(exc: Exception) -> bool:
    """True when the failure means 'this model name cannot be used' (worth trying another)."""
    text = str(exc).lower()
    return (
        _status_code(exc) == 404
        or "no longer available" in text
        or ("not found" in text and "model" in text)
    )


def _is_bad_api_key(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "api key not valid" in text
        or "api_key_invalid" in text
        or "api key expired" in text
        or (_status_code(exc) in (401, 403) and "key" in text)
    )


def call_gemini(model: str, prompt: str, want_json: bool = False, temperature: float = 0.7) -> str:
    """
    Send a prompt to Gemini and return the raw text response.

    Raises GeminiConfigError (missing/invalid key) or GeminiRequestError
    (everything else) so callers only need one try/except.
    """
    client = get_client()

    config_kwargs = {"temperature": temperature}
    if want_json:
        config_kwargs["response_mime_type"] = "application/json"

    candidates = _model_candidates(model)
    last_exc = None

    for index, candidate in enumerate(candidates):
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            text = (response.text or "").strip()
        except Exception as exc:  # noqa: BLE001 - mapped to friendly errors below
            last_exc = exc
            if _is_bad_api_key(exc):
                raise GeminiConfigError(
                    "Gemini rejected the API key. Check GOOGLE_API_KEY in your .env file, "
                    "then restart the server."
                ) from exc
            if _is_model_unavailable(exc) and index < len(candidates) - 1:
                logger.warning("Gemini model '%s' is unavailable; trying '%s'.", candidate, candidates[index + 1])
                continue
            if _status_code(exc) == 429:
                raise GeminiRequestError(
                    "Gemini quota or rate limit reached. Wait a minute and try again."
                ) from exc
            raise GeminiRequestError(f"Gemini API request failed: {str(exc)[:300]}") from exc

        if not text:
            raise GeminiRequestError("Gemini returned an empty response. Please try again.")
        return text

    raise GeminiRequestError(f"Gemini API request failed: {str(last_exc)[:300]}")


# --------------------------------------------------------------------------
# Parsing / normalising AI output
# --------------------------------------------------------------------------
def extract_json(text: str):
    """
    Parse JSON out of a Gemini text response. Handles ```json fences and
    extra commentary around the JSON. Returns a dict/list, or None.
    """
    cleaned = (text or "").strip()

    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # Last resort: take the outermost {...} block.
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def _as_text(value) -> str:
    """Turn any JSON value into readable text (Gemini sometimes returns lists)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return ", ".join(_as_text(v) for v in value if v not in (None, ""))
    if isinstance(value, dict):
        return ", ".join(f"{k}: {_as_text(v)}" for k, v in value.items())
    return str(value)


def _normalize_days(data):
    """
    Return a clean list of day dicts (every PLAN_FIELDS key present, all
    values plain strings) or None if `data` does not contain a usable plan.
    """
    days = data.get("days") if isinstance(data, dict) else data
    if not isinstance(days, list):
        return None

    clean = []
    for i, item in enumerate(days, start=1):
        if not isinstance(item, dict):
            continue
        day = {field: _as_text(item.get(field)) or "-" for field in PLAN_FIELDS}
        if day["day"] == "-":
            day["day"] = f"Day {i}"
        clean.append(day)
    return clean or None


def plan_to_storage_json(raw_text: str) -> str:
    """
    Convert a raw Gemini workout response into the JSON string stored in the
    database: {"days": [...]} when parsing works, otherwise {"raw_text": "..."}
    so a malformed AI response never crashes the app.
    """
    days = _normalize_days(extract_json(raw_text))
    if days:
        return json.dumps({"days": days})
    return json.dumps({"raw_text": raw_text})


def load_plan_for_display(plan_json: str):
    """
    Parse a stored plan string back into {"days": [...]} (structured display)
    or {"raw_text": "..."} (fallback display). Returns None for empty input.
    """
    if not plan_json:
        return None
    try:
        data = json.loads(plan_json)
    except (json.JSONDecodeError, TypeError):
        return {"raw_text": str(plan_json)}

    days = _normalize_days(data)
    if days:
        return {"days": days}
    if isinstance(data, dict) and "raw_text" in data:
        return {"raw_text": _as_text(data["raw_text"])}
    return {"raw_text": json.dumps(data, indent=2)}
