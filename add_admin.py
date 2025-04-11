#!/usr/bin/env python3

import sqlite3
import os
from werkzeug.security import generate_password_hash

# Admin credentials
admin_email = 'admin@example.com'
admin_password = 'adminpassword'

# Database path
db_path = 'lms.db'

def create_admin():
    """Add a known good admin account to the database"""
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found.")
        return False
        
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if roles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='roles'")
        if not cursor.fetchone():
            # Create roles table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(20) UNIQUE NOT NULL,
                description VARCHAR(100)
            )
            ''')
            
            # Insert admin role
            cursor.execute("INSERT INTO roles (id, name, description) VALUES (1, 'admin', 'Administrator')")
        
        # Check if admin role exists
        cursor.execute("SELECT id FROM roles WHERE name='admin'")
        admin_role = cursor.fetchone()
        if not admin_role:
            cursor.execute("INSERT INTO roles (id, name, description) VALUES (1, 'admin', 'Administrator')")
            admin_role_id = 1
        else:
            admin_role_id = admin_role[0]
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            # Create users table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
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
        
        # Check if admin user exists
        cursor.execute("SELECT id FROM users WHERE email=?", (admin_email,))
        admin_user = cursor.fetchone()
        
        if admin_user:
            # Update existing admin password
            password_hash = generate_password_hash(admin_password)
            cursor.execute(
                "UPDATE users SET password_hash=?, is_active=1 WHERE email=?", 
                (password_hash, admin_email)
            )
            print(f"Admin password updated for {admin_email}")
        else:
            # Create new admin user
            password_hash = generate_password_hash(admin_password)
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, password_hash, role_id) VALUES (?, ?, ?, ?, ?)",
                ('Admin', 'User', admin_email, password_hash, admin_role_id)
            )
            print(f"Admin user created: {admin_email}")
        
        # Commit changes
        conn.commit()
        print("Admin credentials:")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    create_admin()