from flask import Flask, redirect, url_for
from flask_login import LoginManager
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
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms/static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.permanent_session_lifetime = timedelta(days=7)

# Initialize database
from lms.utils.db import db
db.init_app(app)

# Import models (after db initialization)
from lms.models.user import User
from lms.utils.db import init_db

# Register blueprints
from lms.routes.auth import auth_bp
from lms.routes.admin import admin_bp
from lms.routes.teacher import teacher_bp
from lms.routes.student import student_bp
from lms.routes.course import course_bp

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(teacher_bp, url_prefix='/teacher')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(course_bp, url_prefix='/courses')

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=False, port=5002)