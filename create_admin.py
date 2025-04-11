#!/usr/bin/env python3

import os
import sys
from getpass import getpass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from flask import Flask
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__, template_folder='lms/templates', static_folder='lms/static')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///lms.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
from lms.utils.db import db
db.init_app(app)

# Import models
from lms.models.user import User, Role

def create_admin():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin role exists
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            logger.info("Creating admin role...")
            admin_role = Role(name='admin', description='Administrator')
            db.session.add(admin_role)
            db.session.commit()
        
        # Create admin user
        email = 'admin@example.com'
        password = 'adminpass'  # In production, use getpass to prompt for password
        
        # Check if the admin user already exists
        existing_admin = User.query.filter_by(email=email).first()
        if existing_admin:
            logger.info(f"Admin user {email} already exists.")
            return
        
        # Create the admin user
        admin = User(
            first_name='Admin',
            last_name='User',
            email=email,
            role_id=admin_role.id
        )
        admin.password_hash = generate_password_hash(password)
        
        db.session.add(admin)
        db.session.commit()
        
        logger.info(f"Admin user created successfully: {email}")

if __name__ == "__main__":
    create_admin()