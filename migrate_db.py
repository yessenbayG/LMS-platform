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
        # Check if users table has certificate fields
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        if 'certificate_path' not in user_columns:
            print("Adding certificate_path column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_path VARCHAR(255)")
            
        if 'certificate_verified' not in user_columns:
            print("Adding certificate_verified column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_verified BOOLEAN DEFAULT 0")
            
        if 'certificate_submitted_at' not in user_columns:
            print("Adding certificate_submitted_at column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_submitted_at TIMESTAMP")
            
        if 'certificate_description' not in user_columns:
            print("Adding certificate_description column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN certificate_description TEXT")
            
        if 'about_me' not in user_columns:
            print("Adding about_me column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN about_me TEXT")
        
        # Check if courses table has necessary columns
        cursor.execute("PRAGMA table_info(courses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'image_path' not in columns:
            print("Adding image_path column to courses table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN image_path VARCHAR(255)")
            
        if 'is_approved' not in columns:
            print("Adding is_approved column to courses table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN is_approved BOOLEAN DEFAULT 0")
            # Set all existing courses to approved
            cursor.execute("UPDATE courses SET is_approved = 1")
        
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
            
        # Check if enrollments table has is_favorite column
        cursor.execute("PRAGMA table_info(enrollments)")
        enrollment_columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_favorite' not in enrollment_columns:
            print("Adding is_favorite column to enrollments table...")
            cursor.execute("ALTER TABLE enrollments ADD COLUMN is_favorite BOOLEAN DEFAULT 0")
        
        # Create messages table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            read BOOLEAN NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (recipient_id) REFERENCES users (id)
        )
        ''')
        
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
        
        # Create wishlist table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id),
            UNIQUE(student_id, course_id)
        )
        ''')
        
        # Create payment subscription plans tables if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS teacher_subscription_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL,
            max_students INTEGER NOT NULL,
            price_per_month INTEGER NOT NULL,
            description TEXT
        )
        ''')
        
        # Check if we need to add payment-related columns to courses
        cursor.execute("PRAGMA table_info(courses)")
        course_columns = [column[1] for column in cursor.fetchall()]
        
        if 'enrollment_price' not in course_columns:
            print("Adding enrollment_price column to courses table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN enrollment_price INTEGER DEFAULT 0")
            
        if 'subscription_plan_id' not in course_columns:
            print("Adding subscription_plan_id column to courses table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN subscription_plan_id INTEGER")
            
        if 'payment_receipt_path' not in course_columns:
            print("Adding payment_receipt_path column to courses table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN payment_receipt_path VARCHAR(255)")
            
        if 'payment_verified' not in course_columns:
            print("Adding payment_verified column to courses table...")
            cursor.execute("ALTER TABLE courses ADD COLUMN payment_verified BOOLEAN DEFAULT 0")
        
        # Check if we need to add payment-related columns to enrollments
        cursor.execute("PRAGMA table_info(enrollments)")
        enrollment_columns = [column[1] for column in cursor.fetchall()]
        
        if 'payment_receipt_path' not in enrollment_columns:
            print("Adding payment_receipt_path column to enrollments table...")
            cursor.execute("ALTER TABLE enrollments ADD COLUMN payment_receipt_path VARCHAR(255)")
            
        if 'payment_amount' not in enrollment_columns:
            print("Adding payment_amount column to enrollments table...")
            cursor.execute("ALTER TABLE enrollments ADD COLUMN payment_amount INTEGER")
            
        if 'payment_verified' not in enrollment_columns:
            print("Adding payment_verified column to enrollments table...")
            cursor.execute("ALTER TABLE enrollments ADD COLUMN payment_verified BOOLEAN DEFAULT 0")
            
        if 'payment_date' not in enrollment_columns:
            print("Adding payment_date column to enrollments table...")
            cursor.execute("ALTER TABLE enrollments ADD COLUMN payment_date TIMESTAMP")
        
        # Check if we need to add subscription plans
        cursor.execute("SELECT COUNT(*) FROM teacher_subscription_plans")
        subscription_plan_count = cursor.fetchone()[0]
        
        if subscription_plan_count == 0:
            print("Adding teacher subscription plans...")
            subscription_plans = [
                ("Standard - Up to 10 students", 10, 20000, "Basic plan for small classes"),
                ("Pro - Up to 30 students", 30, 35000, "Professional plan for medium classes"),
                ("Premium - Up to 100 students", 100, 70000, "Premium plan for large classes"),
                ("Enterprise - Unlimited students", 10000, 100000, "Enterprise plan for unlimited students")
            ]
            
            for plan in subscription_plans:
                cursor.execute('''
                INSERT INTO teacher_subscription_plans (name, max_students, price_per_month, description)
                VALUES (?, ?, ?, ?)
                ''', plan)
            
            print(f"Added {len(subscription_plans)} subscription plans")
    
        # Create upload directories
        course_images_dir = os.path.join('lms', 'static', 'uploads', 'course_images')
        certificates_dir = os.path.join('lms', 'static', 'uploads', 'certificates')
        payment_receipts_dir = os.path.join('lms', 'static', 'uploads', 'payment_receipts')
        os.makedirs(course_images_dir, exist_ok=True)
        os.makedirs(certificates_dir, exist_ok=True)
        os.makedirs(payment_receipts_dir, exist_ok=True)
        
        # Create test messages if the messages table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        if cursor.fetchone():
            print("Messages table exists, checking if we need to add test messages")
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            
            if message_count == 0:
                print("Adding test messages...")
                # Get admin and student IDs
                cursor.execute("SELECT id FROM users WHERE email='admin@example.com'")
                admin = cursor.fetchone()
                cursor.execute("SELECT id FROM users WHERE email='student@example.com'")
                student = cursor.fetchone()
                
                if admin and student:
                    admin_id = admin[0]
                    student_id = student[0]
                    
                    # Add test messages
                    cursor.execute("""
                    INSERT INTO messages (sender_id, recipient_id, content, read)
                    VALUES (?, ?, ?, ?)
                    """, (admin_id, student_id, "Welcome to the LMS! How can I help you?", 0))
                    
                    cursor.execute("""
                    INSERT INTO messages (sender_id, recipient_id, content, read)
                    VALUES (?, ?, ?, ?)
                    """, (student_id, admin_id, "Thanks for the welcome! I have a question about the courses.", 0))
                    
                    print("Test messages added.")
        
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