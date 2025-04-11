import os
import sys
from flask import Flask
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

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

# Import models
from lms.models.user import Role, User
from lms.models.course import Category

def setup_database():
    with app.app_context():
        # Create tables
        print("Creating database tables...")
        db.create_all()
        
        # Create roles
        print("Creating roles...")
        roles = {
            'admin': 'Administrator',
            'teacher': 'Teacher',
            'student': 'Student'
        }
        
        for role_name, description in roles.items():
            existing_role = Role.query.filter_by(name=role_name).first()
            if not existing_role:
                role = Role(name=role_name, description=description)
                db.session.add(role)
        
        # Commit to get role IDs
        db.session.commit()
        
        # Get the roles
        admin_role = Role.query.filter_by(name='admin').first()
        teacher_role = Role.query.filter_by(name='teacher').first()
        student_role = Role.query.filter_by(name='student').first()
        
        if not admin_role or not teacher_role or not student_role:
            print("Error: Could not create roles. Exiting.")
            sys.exit(1)
            
        print(f"Roles created: admin_id={admin_role.id}, teacher_id={teacher_role.id}, student_id={student_role.id}")
        
        # Create admin user if it doesn't exist
        print("Creating users...")
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'adminpassword')
        
        if not User.query.filter_by(email=admin_email).first():
            admin = User(
                first_name='Admin',
                last_name='User',
                email=admin_email,
                password=admin_password,  # password setter handles hashing
                role_id=admin_role.id
            )
            db.session.add(admin)
            print(f"Admin user created: {admin_email}")
        
        # Create demo teacher
        teacher_email = 'teacher@example.com'
        if not User.query.filter_by(email=teacher_email).first():
            teacher = User(
                first_name='Demo',
                last_name='Teacher',
                email=teacher_email,
                password='teacherpass',  # password setter handles hashing
                role_id=teacher_role.id
            )
            db.session.add(teacher)
            print(f"Teacher user created: {teacher_email}")
        
        # Create demo student
        student_email = 'student@example.com'
        if not User.query.filter_by(email=student_email).first():
            student = User(
                first_name='Demo',
                last_name='Student',
                email=student_email,
                password='studentpass',  # password setter handles hashing
                role_id=student_role.id
            )
            db.session.add(student)
            print(f"Student user created: {student_email}")
        
        # Create course categories
        print("Creating course categories...")
        categories = [
            'Computer Science',
            'Mathematics',
            'Physics',
            'Chemistry',
            'Biology',
            'History',
            'Literature',
            'Language',
            'Art',
            'Music'
        ]
        
        for category_name in categories:
            if not Category.query.filter_by(name=category_name).first():
                category = Category(name=category_name)
                db.session.add(category)
        
        # Commit all changes
        db.session.commit()
        print("Database successfully initialized with initial data.")

if __name__ == "__main__":
    setup_database()