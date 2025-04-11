#!/usr/bin/env python3

import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

def verify_credentials():
    """Check if the credentials in the database match expected values"""
    conn = sqlite3.connect('lms.db')
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT id, email, password_hash, role_id FROM users ORDER BY id")
    users = cursor.fetchall()
    
    print("User accounts in database:")
    for user in users:
        user_id, email, password_hash, role_id = user
        
        # Get the role name
        cursor.execute("SELECT name FROM roles WHERE id = ?", (role_id,))
        role_name = cursor.fetchone()[0]
        
        # Define expected password based on role
        expected_password = {
            'admin': 'adminpassword',
            'teacher': 'teacherpass',
            'student': 'studentpass'
        }.get(role_name, None)
        
        # Verify the password
        if expected_password:
            password_match = check_password_hash(password_hash, expected_password)
            print(f"ID: {user_id}, Email: {email}, Role: {role_name}")
            print(f"  Password '{expected_password}' match: {password_match}")
            
            # If password doesn't match, update it
            if not password_match:
                new_hash = generate_password_hash(expected_password)
                cursor.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (new_hash, user_id)
                )
                conn.commit()
                print(f"  Updated password hash for {email}")
        else:
            print(f"ID: {user_id}, Email: {email}, Role: {role_name}")
            print(f"  No expected password defined for this role")
    
    # Insert default users if not found
    default_users = [
        ('admin@example.com', 'adminpassword', 'admin'),
        ('teacher@example.com', 'teacherpass', 'teacher'),
        ('student@example.com', 'studentpass', 'student')
    ]
    
    for email, password, role_name in default_users:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if not cursor.fetchone():
            # Get role id
            cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
            role_id = cursor.fetchone()[0]
            
            # Create user
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (first_name, last_name, email, password_hash, role_id) VALUES (?, ?, ?, ?, ?)",
                ('Default', role_name.capitalize(), email, password_hash, role_id)
            )
            conn.commit()
            print(f"Created missing default user: {email} with role {role_name}")
    
    conn.close()
    print("\nVerification complete. All default users should now be accessible.")
    print("Default credentials:")
    print("- Admin: admin@example.com / adminpassword")
    print("- Teacher: teacher@example.com / teacherpass")
    print("- Student: student@example.com / studentpass")

if __name__ == "__main__":
    verify_credentials()