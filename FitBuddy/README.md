# FitBuddy – AI Fitness Plan Generator

FitBuddy is an AI-powered web application that generates a personalized
7-day workout plan and a nutrition/recovery tip using Google's Gemini
models. Users can submit feedback on their plan (e.g. "add more cardio")
and FitBuddy will use Gemini to generate a revised plan — both the
original and the updated plan are kept in the database. Built as a BCA
final-year academic project.

---

## Features

- Collects user details (name, user ID, age, weight, fitness goal, workout intensity)
- Generates a structured **7-day workout plan** using Gemini (day, focus, warm-up,
  exercises, sets/reps/duration, rest, cooldown)
- Generates a short **nutrition/recovery tip** using a fast Gemini model
- **Feedback-driven regeneration** — submit feedback and Gemini revises the plan
  (original plan is never overwritten; both versions are stored)
- **Admin dashboard** (`/view-all-users`) with search and simple statistics
  (total users, total plans, updated plans, goals distribution)
- Graceful error handling — missing API key, Gemini failures, invalid input,
  and malformed AI responses never crash the app or expose stack traces
- Auto-created SQLite database — no manual SQL setup
- Interactive API docs via Swagger UI (`/docs`)
- Responsive, modern fitness-themed UI (desktop + mobile)

---

## Technology Stack

| Layer      | Technology                                   |
|------------|-----------------------------------------------|
| Backend    | Python, FastAPI, Uvicorn                      |
| Frontend   | HTML, CSS, Jinja2 templates, vanilla JS       |
| Database   | SQLite + SQLAlchemy ORM                       |
| AI         | Google Gemini API (`google-genai` SDK)        |
| Validation | Pydantic                                      |

---

## Project Structure

```
FitBuddy/
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entrypoint
│   ├── routes.py                  # Request handling / page rendering
│   ├── database.py                # DB engine, session, init_db()
│   ├── models.py                  # SQLAlchemy models: User, WorkoutPlan
│   ├── schemas.py                 # Pydantic validation schemas
│   ├── gemini_client.py           # Centralized Gemini service layer
│   ├── gemini_generator.py        # Workout plan generation (workout model)
│   ├── gemini_flash_generator.py  # Nutrition tip generation (tip model)
│   └── updated_plan.py            # Feedback-based plan revision
│
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── result.html
│   ├── feedback.html
│   ├── all_users.html
│   └── error.html
│
├── static/
│   ├── css/style.css
│   └── js/script.js
│
├── .env                # Your real API key goes here (not committed)
├── .env.example        # Template with no real credentials
├── .gitignore
├── requirements.txt
├── README.md
└── run.bat             # One-click setup + run script for Windows
```

---

## Requirements

- Python 3.10 or newer (developed and checked with Python 3.12)
- Internet access (for `pip install` and for calling the Gemini API)
- A Google Gemini API key (free tier available)
- Windows 10/11 (the project also runs on macOS/Linux, but `run.bat` is Windows-specific)

---

## Installation (Windows)

### Option A — the easy way

Just double-click **`run.bat`**, or run it from a command prompt in the project folder:

```
run.bat
```

It will automatically:
1. Check that Python is installed
2. Create a virtual environment (`venv/`) if one doesn't exist
3. Activate the virtual environment
4. Install dependencies from `requirements.txt` (skipped if already installed)
5. Start the Uvicorn server

### Option B — manual setup

Open a command prompt in the project folder and run:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Gemini API Key Setup

1. Go to [Google AI Studio](https://aistudio.google.com/apikey) and sign in with a Google account.
2. Click **Create API key** and copy the generated key.
3. Open the `.env` file in the project root and replace the placeholder:

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

with your real key, e.g.:

```
GOOGLE_API_KEY=AIzaSyD-your-real-key-here
```

4. Save the file and (re)start the server.

**Never commit your real `.env` file** — it's already excluded via `.gitignore`.
Share `.env.example` instead if you need to hand the project to someone else.

---

## .env Configuration Reference

| Variable                 | Purpose                                                                 | Default                              |
|--------------------------|-------------------------------------------------------------------------|--------------------------------------|
| `GOOGLE_API_KEY`         | Your Gemini API key (required)                                           | *(none — required)*                  |
| `GEMINI_WORKOUT_MODEL`   | Model for the 7-day plan and feedback revisions                          | `gemini-3.6-flash`                   |
| `GEMINI_TIP_MODEL`       | Model for the short nutrition/recovery tip                               | `gemini-3.5-flash-lite`              |
| `GEMINI_FALLBACK_MODELS` | Comma-separated models tried automatically if a model returns 404        | `gemini-3.5-flash,gemini-3.6-flash`  |

The `.env` file is read from the project folder, no matter where you start the
server from. Restart the server after editing it.

### A note on model names

Google retires and restricts Gemini model names regularly. The original spec's
"Gemini 1.5 Pro / Flash" no longer exist, and the Gemini 2.5 models are now
limited to accounts that already used them (new projects get a
*"no longer available to new users"* 404). FitBuddy keeps the same two logical
roles from the spec — one model for plan generation/revision and one light
model for the short tip — mapped onto current stable models, and it
automatically tries `GEMINI_FALLBACK_MODELS` if the configured model returns 404.

Want stronger reasoning for the workout plan? Set
`GEMINI_WORKOUT_MODEL=gemini-3.1-pro-preview` (a preview model; it may require
billing on your Google account). Check https://ai.google.dev/gemini-api/docs/models
for the current model list.

---

## How to Run

```
uvicorn app.main:app --reload
```

(or simply run `run.bat`)

Then open your browser to:

- **App:** http://127.0.0.1:8000
- **Swagger API docs:** http://127.0.0.1:8000/docs

The SQLite database file (`fitbuddy.db`) is created automatically in the
project root the first time the server starts — no manual setup needed.

---

## Database Information

- **Engine:** SQLite (file: `fitbuddy.db`, created automatically)
- **ORM:** SQLAlchemy
- **Tables:**
  - `users` — one row per user (`user_id`, name, age, weight, goal, intensity, created_at)
  - `workout_plans` — one row per generated plan, linked to a user via `user_id`
    (`original_plan`, `updated_plan`, `nutrition_tip`, `feedback`, timestamps)

You can inspect the database with any SQLite browser (e.g. "DB Browser for SQLite")
by opening the `fitbuddy.db` file after running the app at least once.

---

## Example User Input

| Field              | Example value       |
|---------------------|---------------------|
| Name                | Priya Sharma        |
| User ID             | student001          |
| Age                 | 21                  |
| Weight (kg)         | 58                  |
| Fitness Goal        | Muscle Gain         |
| Workout Intensity   | Medium              |

## Example Workflow

1. Open http://127.0.0.1:8000 and fill in the form above, then click **Generate Plan**.
2. FitBuddy calls Gemini to generate a structured 7-day plan and a nutrition tip,
   saves both to the database, and shows the **Result** page.
3. On the Result page, type feedback such as *"Add more cardio and include an
   extra rest day"* and click **Update My Plan**.
4. FitBuddy sends the original plan + your feedback to Gemini, gets back a revised
   7-day plan, stores it as the `updated_plan` (the original is kept untouched),
   and shows the updated plan with a success message.
5. Visit http://127.0.0.1:8000/view-all-users to see every user, their original
   and updated plans (expandable), feedback given, and dashboard statistics.

---

## Routes

| Method | Endpoint             | Purpose                                             | Parameters / form fields                                   |
|--------|----------------------|-----------------------------------------------------|------------------------------------------------------------|
| GET    | `/`                  | Home page with the plan form                        | —                                                          |
| POST   | `/generate-workout`  | Validate input, call Gemini, save and show the plan | `name`, `user_id`, `age`, `weight`, `goal`, `intensity`    |
| GET    | `/feedback/{user_id}`| Feedback page for an existing user                  | `user_id` in the path                                      |
| POST   | `/submit-feedback`   | Revise the latest plan with Gemini, save the update | `user_id`, `feedback`                                      |
| GET    | `/view-all-users`    | Admin dashboard, statistics and search              | optional `q` (matches name or user ID)                     |
| GET    | `/docs`              | Swagger UI                                          | —                                                          |

Validation rules: age 10–100, weight 0–400 kg, goal and intensity must be one of
the listed options, User ID up to 64 characters (letters, numbers, `_`, `-`, `.`),
feedback up to 1000 characters. Invalid input shows a friendly error page.

Behaviour notes:

- Each *Generate Plan* submit creates a new plan row; feedback always applies to
  the user's most recent plan.
- Feedback is applied to the **original** plan and stored as `updated_plan`; the
  original is never overwritten. Submitting feedback again replaces the previous
  update (and its feedback text) for that plan.
- If the nutrition tip fails but the workout plan succeeds, the plan is still saved
  and shown.
- The database is only written **after** Gemini succeeds, so a failed AI call never
  creates or changes a user.
- There is no login. Anyone who can open the site can see `/view-all-users`, so use
  this project on a local machine or trusted network only.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `GOOGLE_API_KEY is not set` error page | Edit `.env` and add your real Gemini API key, then restart the server. |
| `Gemini rejected the API key` | The key in `.env` is wrong, expired, or still the placeholder. Create a new key at Google AI Studio and restart. |
| `404` / `no longer available` model errors | The model in `.env` was retired or restricted. Set `GEMINI_WORKOUT_MODEL` / `GEMINI_TIP_MODEL` to a current model (see the model note above). Fallback models are tried automatically first. |
| `quota or rate limit reached` | Free-tier limits hit. Wait a minute and retry, or use a lighter model. |
| "FitBuddy could not reach the AI service" | Check your internet connection and that your API key is valid/has quota. Try again. |
| `run.bat` says Python was not found | Install Python 3.10+ from python.org and make sure "Add to PATH" is checked during install. |
| Port 8000 already in use | Run `python -m uvicorn app.main:app --reload --port 8001` and open that port instead. |
| `TypeError: unhashable type: 'dict'` on the home page | Caused by the old `TemplateResponse(name, context)` call style with current Starlette. Fixed in this version (`TemplateResponse(request, name, context)`). |
| Plan shows as raw text instead of day cards | This is the built-in fallback for when Gemini's response isn't valid JSON — the app won't crash, it just shows the raw AI text instead. Try generating again. |
| Changes to `.env` not taking effect | Stop the server (CTRL+C) and restart it — environment variables are only read at startup. |

---

## Academic Concepts Demonstrated

- Generative AI / Large Language Models (Google Gemini)
- REST API design with FastAPI
- Server-side rendering with Jinja2 templates
- ORM-based database access with SQLAlchemy (CRUD operations)
- Relational data modeling (User ↔ WorkoutPlan one-to-many relationship)
- Input validation with Pydantic
- Feedback-driven AI regeneration loop
- Responsive front-end design (HTML/CSS/JS)
