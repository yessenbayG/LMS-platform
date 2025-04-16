from datetime import datetime
from flask_login import UserMixin
from lms.utils.db import db
from werkzeug.security import generate_password_hash, check_password_hash

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(100))
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Teacher certification fields
    certificate_path = db.Column(db.String(255), nullable=True, default=None)
    certificate_verified = db.Column(db.Boolean, nullable=True, default=False)
    certificate_submitted_at = db.Column(db.DateTime, nullable=True, default=None)
    
    # Relationships
    created_courses = db.relationship('Course', backref='teacher', lazy='dynamic')
    enrollments = db.relationship('Enrollment', back_populates='student', lazy='dynamic')
    submissions = db.relationship('Submission', back_populates='student', lazy='dynamic')
    # Message relationships are defined in the Message model using foreign_keys
    
    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        try:
            result = check_password_hash(self.password_hash, password)
            return result
        except Exception as e:
            print(f"Error verifying password: {str(e)}")
            return False
    
    def is_admin(self):
        return self.role.name == 'admin'
    
    def is_teacher(self):
        return self.role.name == 'teacher'
    
    def is_student(self):
        return self.role.name == 'student'
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_verified_certificate(self):
        try:
            return self.certificate_verified and self.certificate_path is not None
        except:
            # If the certificate fields don't exist
            return False
    
    def can_create_courses(self):
        try:
            return self.is_teacher() and self.has_verified_certificate()
        except:
            # Default to True if the certificate fields don't exist
            return self.is_teacher()
    
    def __repr__(self):
        return f'<User {self.email}>'