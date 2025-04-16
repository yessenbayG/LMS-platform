from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
import sys

db = SQLAlchemy()

def init_db():
    """Initialize the database and create admin user if needed"""
    from lms.models.user import User, Role
    from lms.models.message import Message
    
    print("Creating all database tables...")
    db.create_all()
    
    # Create roles if they don't exist
    roles = {
        'admin': 'Administrator',
        'teacher': 'Teacher',
        'student': 'Student'
    }
    
    for role_name, description in roles.items():
        if not Role.query.filter_by(name=role_name).first():
            role = Role(name=role_name, description=description)
            db.session.add(role)
    
    # Commit to save roles first
    db.session.commit()
    
    # Verify roles exist
    admin_role = Role.query.filter_by(name='admin').first()
    if not admin_role:
        print("Error: Admin role could not be created.")
        return
        
    # Create admin user if it doesn't exist
    admin_email = os.getenv('ADMIN_EMAIL', 'admin@gmail.com')
    admin_password = os.getenv('ADMIN_PASSWORD', 'qweasdqwe123')
    
    existing_admin = User.query.filter_by(email=admin_email).first()
    if not existing_admin:
        admin = User(
            first_name='Admin',
            last_name='User',
            email=admin_email,
            password=admin_password, # Using password setter method
            role_id=admin_role.id
        )
        db.session.add(admin)
        print(f"Admin user created: {admin_email}")
    
    # Create demo accounts
    teacher_role = Role.query.filter_by(name='teacher').first()
    student_role = Role.query.filter_by(name='student').first()
    
    if teacher_role and not User.query.filter_by(email='teacher@example.com').first():
        teacher = User(
            first_name='Demo',
            last_name='Teacher',
            email='teacher@gmail.com',
            password='qweasdqwe123', # Using password setter method
            role_id=teacher_role.id
        )
        db.session.add(teacher)
        print("Demo teacher account created")
        
    if student_role and not User.query.filter_by(email='student@example.com').first():
        student = User(
            first_name='Demo',
            last_name='Student',
            email='student@gmail.com',
            password='qweasdqwe123', # Using password setter method
            role_id=student_role.id
        )
        db.session.add(student)
        print("Demo student account created")
    
    # Commit all changes
    db.session.commit()
    print("Database initialized successfully.")