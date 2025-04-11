#!/usr/bin/env python3

import os
import sqlite3
from flask import Flask
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

# Setup Flask app
app = Flask(
    __name__,
    template_folder='lms/templates',
    static_folder='lms/static'
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///lms.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import db after app config
from lms.utils.db import db
db.init_app(app)

def upgrade_database():
    """Add new tables and columns to the database"""
    db_path = 'instance/lms.db'
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}. Checking alternate path...")
        db_path = 'lms.db'
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path} either. Please check database location.")
            sys.exit(1)

    print(f"Using database at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist and add them if they don't
    try:
        # Check if image_path column exists in courses table
        cursor.execute("PRAGMA table_info(courses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'image_path' not in columns:
            print("Adding image_path column to courses table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN image_path VARCHAR(255)")
        
        # Check if overall_grade column exists in enrollments table
        cursor.execute("PRAGMA table_info(enrollments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'overall_grade' not in columns:
            print("Adding overall_grade column to enrollments table...")
            cursor.execute("ALTER TABLE enrollments ADD COLUMN overall_grade FLOAT")
        
        # Check if existing tables need updating
        cursor.execute("PRAGMA table_info(materials)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'module_id' not in columns:
            print("Adding module_id column to materials table...")
            cursor.execute("ALTER TABLE materials ADD COLUMN module_id INTEGER")
        
        if 'order' not in columns:
            print("Adding order column to materials table...")
            cursor.execute("ALTER TABLE materials ADD COLUMN \"order\" INTEGER DEFAULT 0")
        
        # Create new tables
        print("Creating new tables...")
        
        # Create modules table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            "order" INTEGER DEFAULT 0,
            course_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
        ''')
        
        # Create tests table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(100) NOT NULL,
            description TEXT,
            passing_score FLOAT DEFAULT 70.0,
            module_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (module_id) REFERENCES modules (id)
        )
        ''')
        
        # Create questions table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_text TEXT NOT NULL,
            question_type VARCHAR(20) NOT NULL,
            points FLOAT DEFAULT 1.0,
            test_id INTEGER NOT NULL,
            FOREIGN KEY (test_id) REFERENCES tests (id)
        )
        ''')
        
        # Create question_options table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            option_text TEXT NOT NULL,
            is_correct BOOLEAN DEFAULT 0,
            question_id INTEGER NOT NULL,
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
        ''')
        
        # Create test_attempts table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            test_id INTEGER NOT NULL,
            score FLOAT,
            passed BOOLEAN,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (test_id) REFERENCES tests (id)
        )
        ''')
        
        # Create test_answers table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer_text TEXT,
            selected_options VARCHAR(255),
            points_earned FLOAT DEFAULT 0,
            FOREIGN KEY (attempt_id) REFERENCES test_attempts (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
        ''')
        
        # Create module_progress table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS module_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            completed BOOLEAN DEFAULT 0,
            completed_at TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (module_id) REFERENCES modules (id),
            UNIQUE(student_id, module_id)
        )
        ''')
        
        # Create upload directories
        upload_dir = os.path.join('lms', 'static', 'uploads', 'course_images')
        os.makedirs(upload_dir, exist_ok=True)
        
        conn.commit()
        print("Database upgraded successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error upgrading database: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    upgrade_database()