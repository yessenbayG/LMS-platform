#!/usr/bin/env python3

import os
import sys
import argparse
import logging
from datetime import datetime

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

def create_admin(email, password, first_name, last_name):
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
        
        # Check if the admin user already exists
        existing_admin = User.query.filter_by(email=email).first()
        if existing_admin:
            logger.info(f"Admin user {email} already exists.")
            return
        
        # Create the admin user
        admin = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            role_id=admin_role.id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        admin.password_hash = generate_password_hash(password)
        
        try:
            db.session.add(admin)
            db.session.commit()
            logger.info(f"Admin user created successfully: {email}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating admin user: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create an admin user for the LMS.')
    parser.add_argument('--email', required=True, help='Admin email address')
    parser.add_argument('--password', required=True, help='Admin password')
    parser.add_argument('--first_name', required=True, help='Admin first name')
    parser.add_argument('--last_name', required=True, help='Admin last name')
    
    args = parser.parse_args()
    
    create_admin(args.email, args.password, args.first_name, args.last_name)