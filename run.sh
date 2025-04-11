#!/bin/bash

# Set up Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Create uploads directory if it doesn't exist
mkdir -p lms/static/uploads

# Initialize database with demo data
echo "Setting up database..."
python setup_db.py

# Run the application
echo "Starting LMS application..."
python app.py