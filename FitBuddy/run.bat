@echo off
setlocal

REM Always work from the folder this script lives in, wherever it was launched from.
cd /d "%~dp0"

echo ============================================
echo   FitBuddy - AI Fitness Plan Generator
echo ============================================

REM 1. Check Python is installed
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    echo Please install Python 3.10 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

REM 2. Create the virtual environment if it does not exist yet
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Could not create the virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists, skipping creation.
)

REM 3. Activate the virtual environment
call "venv\Scripts\activate.bat"

REM 4. Install dependencies if any required package is missing
python -c "import fastapi, uvicorn, sqlalchemy, jinja2, dotenv, google.genai" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Dependency installation failed. Check your internet connection and try again.
        pause
        exit /b 1
    )
) else (
    echo Dependencies already installed, skipping install.
    echo Delete the venv folder and run this script again to force a reinstall.
)

REM 5. Create .env from the template if it is missing
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo Created .env from .env.example.
    )
)

REM 6. Warn if .env still has the placeholder API key
findstr /C:"your_gemini_api_key_here" ".env" >nul 2>nul
if not errorlevel 1 (
    echo.
    echo WARNING: .env still contains the placeholder API key.
    echo Edit the .env file and set GOOGLE_API_KEY to your real Gemini API key.
    echo.
)

REM 7. Start the FastAPI server
echo.
echo Starting FitBuddy at http://127.0.0.1:8000  - Swagger docs at http://127.0.0.1:8000/docs
echo Press CTRL+C to stop the server.
echo.
python -m uvicorn app.main:app --reload

pause
