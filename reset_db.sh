#!/bin/bash

# ANSI color codes for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== LMS Database Reset Script ===${NC}"
echo -e "${YELLOW}WARNING: This will reset your database to a clean state${NC}"
echo -e "${YELLOW}All data including users, courses, and submissions will be deleted${NC}"

# Ask for confirmation
read -p "Are you sure you want to continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${RED}Operation cancelled${NC}"
    exit 1
fi

echo -e "${BLUE}Removing existing database files...${NC}"

# Remove database files
rm -f instance/lms.db
rm -f lms.db

echo -e "${GREEN}Database files removed successfully${NC}"

# Create required directories
echo -e "${BLUE}Creating required directories...${NC}"
mkdir -p instance
mkdir -p lms/static/uploads/course_images
mkdir -p lms/static/uploads/certificates

echo -e "${BLUE}Running database setup...${NC}"

# Create database schema and initial data
python setup_db.py

echo -e "${BLUE}Adding admin accounts...${NC}"

# Create admin accounts
python create_admin.py --email admin@gmail.com --password qweasdqwe123 --first_name Admin --last_name User

echo -e "${GREEN}Admin account created: admin@gmail.com / qweasdqwe123${NC}"

# Ask if user wants to create a teacher account
read -p "Do you want to create a test teacher account? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${BLUE}Creating test teacher account...${NC}"
    
    # Create teacher role in the database if it doesn't exist
    python3 -c "from lms.utils.db import db; from lms.models.user import User, Role; from app import app; with app.app_context(): teacher_role = Role.query.filter_by(name='teacher').first(); if not teacher_role: teacher_role = Role(name='teacher', description='Teacher role'); db.session.add(teacher_role); db.session.commit(); print('Teacher role created');"
    
    # Create teacher account
    python3 -c "from werkzeug.security import generate_password_hash; from datetime import datetime; from lms.utils.db import db; from lms.models.user import User, Role; from app import app; with app.app_context(): teacher_role = Role.query.filter_by(name='teacher').first(); if teacher_role: teacher = User(first_name='Test', last_name='Teacher', email='teacher@example.com', password_hash=generate_password_hash('teacher123'), role_id=teacher_role.id, is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow()); db.session.add(teacher); db.session.commit(); print('Teacher created');"
    
    echo -e "${GREEN}Teacher account created: teacher@example.com / teacher123${NC}"
fi

# Ask if user wants to create a student account
read -p "Do you want to create a test student account? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${BLUE}Creating test student account...${NC}"
    
    # Create student role in the database if it doesn't exist
    python3 -c "from lms.utils.db import db; from lms.models.user import User, Role; from app import app; with app.app_context(): student_role = Role.query.filter_by(name='student').first(); if not student_role: student_role = Role(name='student', description='Student role'); db.session.add(student_role); db.session.commit(); print('Student role created');"
    
    # Create student account
    python3 -c "from werkzeug.security import generate_password_hash; from datetime import datetime; from lms.utils.db import db; from lms.models.user import User, Role; from app import app; with app.app_context(): student_role = Role.query.filter_by(name='student').first(); if student_role: student = User(first_name='Test', last_name='Student', email='student@example.com', password_hash=generate_password_hash('student123'), role_id=student_role.id, is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow()); db.session.add(student); db.session.commit(); print('Student created');"
    
    echo -e "${GREEN}Student account created: student@example.com / student123${NC}"
fi

echo -e "${BLUE}Running database migration to ensure all schema updates...${NC}"
python migrate_db.py

echo -e "${GREEN}Database reset and setup complete!${NC}"
echo -e "${YELLOW}You can now run the application with ./run.sh${NC}"