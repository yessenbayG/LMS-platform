@echo off
rem Windows batch script for running the LMS application

rem Set up Python virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

rem Activate virtual environment
call venv\Scripts\activate.bat

rem Install requirements
echo Installing dependencies...
pip install -r requirements.txt

rem Create uploads directory if it doesn't exist
if not exist lms\static\uploads (
    mkdir lms\static\uploads
)

rem Initialize database with demo data
echo Setting up database...
python setup_db.py

rem Run the application
echo Starting LMS application...
python app.py

pause