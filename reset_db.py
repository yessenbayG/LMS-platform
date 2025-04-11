#!/usr/bin/env python3

import os
import sys
import sqlite3
import logging
from werkzeug.security import generate_password_hash

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables(db_path):
    # Remove the existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed existing database: {db_path}")

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
    
    # Generate password hashes with the right method for Flask-Login
    admin_pass = generate_password_hash('adminpassword', method='pbkdf2:sha256')
    teacher_pass = generate_password_hash('teacherpass', method='pbkdf2:sha256')
    student_pass = generate_password_hash('studentpass', method='pbkdf2:sha256')
    
    # Insert default users
    users = [
        ('Admin', 'User', 'admin@example.com', admin_pass, 1),  # Admin
        ('Demo', 'Teacher', 'teacher@example.com', teacher_pass, 2),  # Teacher
        ('Demo', 'Student', 'student@example.com', student_pass, 3)   # Student
    ]
    cursor.executemany(
        'INSERT INTO users (first_name, last_name, email, password_hash, role_id) VALUES (?, ?, ?, ?, ?)', 
        users
    )
    
    # Insert categories
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
    
    # Commit and close
    conn.commit()
    conn.close()
    
    logger.info(f"Database created successfully at {db_path}")
    logger.info("Created roles: Admin, Teacher, Student")
    logger.info("Created default users:")
    logger.info("  - Admin: admin@example.com / adminpassword")
    logger.info("  - Teacher: teacher@example.com / teacherpass")
    logger.info("  - Student: student@example.com / studentpass")

if __name__ == "__main__":
    db_path = 'lms.db'
    create_tables(db_path)