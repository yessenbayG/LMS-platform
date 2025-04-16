import os
import sqlite3
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Get the absolute path to the instance folder
instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
db_path = os.path.join(instance_path, 'lms.db')

# Create a minimal application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy and Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import your models
from lms.models.user import User, Role
from lms.models.course import Course, Category, Material, Assignment, Submission, Enrollment
from lms.models.course import Module, Test, Question, QuestionOption, TestAttempt, TestAnswer, ModuleProgress
from lms.models.message import Message

def add_certificate_fields():
    """Add certificate fields to users table"""
    # First, check if the database file exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, checking for lms.db in root directory")
        db_path_alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms.db')
        if os.path.exists(db_path_alt):
            global db_path
            db_path = db_path_alt
        else:
            print(f"Database not found at {db_path_alt} either")
            return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    try:
        # Add certificate fields if they don't exist
        if 'certificate_path' not in column_names:
            print("Adding certificate_path column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_path VARCHAR(255)")
        
        if 'certificate_verified' not in column_names:
            print("Adding certificate_verified column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_verified BOOLEAN DEFAULT 0")
        
        if 'certificate_submitted_at' not in column_names:
            print("Adding certificate_submitted_at column to users table")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_submitted_at TIMESTAMP")
        
        conn.commit()
        print("Successfully added certificate fields to users table")
    except sqlite3.Error as e:
        print(f"Error adding columns: {e}")
    finally:
        conn.close()

def add_is_active_to_courses():
    """Add is_active column to courses table with default value True"""
    # Check if column already exists
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(courses)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'is_active' in column_names:
        print("is_active column already exists in courses table")
        conn.close()
        return
    
    try:
        # Add is_active column with default value True
        cursor.execute("ALTER TABLE courses ADD COLUMN is_active BOOLEAN DEFAULT 1")
        conn.commit()
        print("Successfully added is_active column to courses table")
    except sqlite3.Error as e:
        print(f"Error adding column: {e}")
    finally:
        conn.close()

def run_migrations():
    """Run Flask-Migrate migrations"""
    print("Running Flask-Migrate migrations...")
    try:
        # Try to initialize migrations if needed
        os.system('FLASK_APP=migrations.py flask db init')
    except:
        print("Migration directory may already exist, skipping initialization.")
    
    os.system('FLASK_APP=migrations.py flask db migrate -m "Add teacher certificate fields"')
    os.system('FLASK_APP=migrations.py flask db upgrade')
    print("Flask-Migrate migrations completed.")

if __name__ == "__main__":
    print("Running database migrations...")
    
    # First try the direct SQLite approach for backward compatibility
    add_certificate_fields()
    add_is_active_to_courses()
    
    # Then try to run Flask-Migrate migrations
    run_migrations()
    
    print("All migrations completed.")