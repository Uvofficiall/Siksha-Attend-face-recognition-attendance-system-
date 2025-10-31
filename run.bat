@echo off
echo Starting Siksha Attend Application...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if Firebase credentials exist
if not exist "firebase-credentials.json" (
    echo.
    echo WARNING: firebase-credentials.json not found!
    echo Please copy your Firebase service account key to firebase-credentials.json
    echo.
    pause
    exit /b 1
)

REM Run the application
echo.
echo Starting Flask application...
echo Open http://localhost:5000 in your browser
echo.
python app.py

pause