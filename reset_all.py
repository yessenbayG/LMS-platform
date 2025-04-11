#!/usr/bin/env python3

import os
import sqlite3
from werkzeug.security import generate_password_hash

def reset_database():
    """Reset the database and create admin, teacher, and student accounts"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'lms.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Remove the existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")

    # Create a new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create roles table
    cursor.execute('''
    CREATE TABLE roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(20) UNIQUE NOT NULL,
        description VARCHAR(100)
    )
    ''')
    
    # Create users table
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(256) NOT NULL,
        role_id INTEGER NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (role_id) REFERENCES roles (id)
    )
    ''')
    
    # Create categories table
    cursor.execute('''
    CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(50) UNIQUE NOT NULL,
        description VARCHAR(200)
    )
    ''')
    
    # Insert roles
    roles = [
        (1, 'admin', 'Administrator'),
        (2, 'teacher', 'Teacher'),
        (3, 'student', 'Student')
    ]
    cursor.executemany('INSERT INTO roles (id, name, description) VALUES (?, ?, ?)', roles)
    
    # Insert default users with stable password hashes
    admin_hash = generate_password_hash('adminpassword', method='pbkdf2:sha256')
    teacher_hash = generate_password_hash('teacherpass', method='pbkdf2:sha256')
    student_hash = generate_password_hash('studentpass', method='pbkdf2:sha256')
    
    users = [
        ('Admin', 'User', 'admin@example.com', admin_hash, 1),  # Admin
        ('Demo', 'Teacher', 'teacher@example.com', teacher_hash, 2),  # Teacher
        ('Demo', 'Student', 'student@example.com', student_hash, 3)   # Student
    ]
    cursor.executemany(
        'INSERT INTO users (first_name, last_name, email, password_hash, role_id) VALUES (?, ?, ?, ?, ?)', 
        users
    )
    
    # Create default categories
    categories = [
        ('Computer Science',),
        ('Mathematics',),
        ('Physics',),
        ('Chemistry',),
        ('Biology',),
        ('History',),
        ('Literature',),
        ('Language',),
        ('Art',),
        ('Music',)
    ]
    cursor.executemany('INSERT INTO categories (name) VALUES (?)', categories)
    
    # Add the necessary tables for the LMS functionality
    # Courses table
    cursor.execute('''
    CREATE TABLE courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(100) NOT NULL,
        description TEXT,
        category_id INTEGER,
        teacher_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (teacher_id) REFERENCES users (id)
    )
    ''')
    
    # Materials table
    cursor.execute('''
    CREATE TABLE materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(100) NOT NULL,
        content_type VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        file_path VARCHAR(255),
        course_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses (id)
    )
    ''')
    
    # Assignments table
    cursor.execute('''
    CREATE TABLE assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        course_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (course_id) REFERENCES courses (id)
    )
    ''')
    
    # Submissions table
    cursor.execute('''
    CREATE TABLE submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT,
        file_path VARCHAR(255),
        student_id INTEGER NOT NULL,
        assignment_id INTEGER NOT NULL,
        grade FLOAT,
        feedback TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        graded_at TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users (id),
        FOREIGN KEY (assignment_id) REFERENCES assignments (id)
    )
    ''')
    
    # Enrollments table
    cursor.execute('''
    CREATE TABLE enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users (id),
        FOREIGN KEY (course_id) REFERENCES courses (id),
        UNIQUE (student_id, course_id)
    )
    ''')
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"Database reset completed successfully")
    print("Default credentials:")
    print("Admin: admin@example.com / adminpassword")
    print("Teacher: teacher@example.com / teacherpass")
    print("Student: student@example.com / studentpass")

if __name__ == "__main__":
    reset_database()