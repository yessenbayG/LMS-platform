from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(
    __name__,
    template_folder='lms/templates',
    static_folder='lms/static'
)

# App configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///lms.db')
app.config['SQLALCHEMY_ECHO'] = True  # Log SQL queries for debugging
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms/static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.permanent_session_lifetime = timedelta(days=7)

# Initialize database
from lms.utils.db import db
db.init_app(app)

# Setup CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Import models (after db initialization)
from lms.models.user import User
from lms.models.message import Message
from lms.utils.db import init_db

# Enable more detailed error logging
app.config['PROPAGATE_EXCEPTIONS'] = True

# Register blueprints
from lms.routes.auth import auth_bp
from lms.routes.admin import admin_bp
from lms.routes.teacher import teacher_bp
from lms.routes.student import student_bp
from lms.routes.course import course_bp
from lms.routes.messages import messages_bp
from swagger import swagger_bp

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(course_bp, url_prefix='/courses')
app.register_blueprint(messages_bp, url_prefix='/messages')
app.register_blueprint(swagger_bp)

@app.route('/')
def index():
    return render_template('landing.html')

if __name__ == '__main__':
    with app.app_context():
        init_db()
        
        # Ensure the messages table exists and create it if needed
        try:
            from lms.models.message import Message
            
            # Check if messages table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'messages' not in inspector.get_table_names():
                print("Creating messages table...")
                Message.__table__.create(db.engine)
                print("Messages table created.")
                
                # Create test messages
                admin = User.query.filter_by(email='admin@example.com').first()
                student = User.query.filter_by(email='student@example.com').first()
                
                if admin and student:
                    test_message = Message(
                        sender_id=admin.id,
                        recipient_id=student.id,
                        content='Welcome to the LMS! How can I help you?'
                    )
                    db.session.add(test_message)
                    
                    test_reply = Message(
                        sender_id=student.id,
                        recipient_id=admin.id,
                        content='Thanks for the welcome! I have a question about the courses.'
                    )
                    db.session.add(test_reply)
                    
                    db.session.commit()
                    print("Test messages created.")
        except Exception as e:
            print(f"Error setting up messages: {str(e)}")
    
    app.run(debug=True, port=5002)