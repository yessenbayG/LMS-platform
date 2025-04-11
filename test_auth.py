#!/usr/bin/env python3

import unittest
from flask import Flask, session
from flask_testing import TestCase
from app import app
from lms.utils.db import db
from lms.models.user import User, Role
import os

class AuthenticationTests(TestCase):
    def create_app(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_lms.db'
        return app
    
    def setUp(self):
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
        
        # Get role IDs
        admin_role = Role.query.filter_by(name='admin').first()
        student_role = Role.query.filter_by(name='student').first()
        
        # Create test users only if they don't exist
        if not User.query.filter_by(email='test_admin@example.com').first():
            test_admin = User(
                first_name='Test',
                last_name='Admin',
                email='test_admin@example.com',
                password='testadminpass',
                role_id=admin_role.id
            )
            db.session.add(test_admin)
        
        if not User.query.filter_by(email='test_student@example.com').first():
            test_student = User(
                first_name='Test',
                last_name='Student',
                email='test_student@example.com',
                password='teststudentpass',
                role_id=student_role.id
            )
            db.session.add(test_student)
        
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        if os.path.exists('test_lms.db'):
            os.remove('test_lms.db')
    
    def test_login_success_admin(self):
        """Test successful login for admin user"""
        response = self.client.post('/login', data={
            'email': 'test_admin@example.com',
            'password': 'testadminpass'
        }, follow_redirects=True)
        
        self.assert200(response)
        self.assertIn(b'Admin Dashboard', response.data)
    
    def test_login_success_student(self):
        """Test successful login for student user"""
        response = self.client.post('/login', data={
            'email': 'test_student@example.com',
            'password': 'teststudentpass'
        }, follow_redirects=True)
        
        self.assert200(response)
        self.assertIn(b'Student Dashboard', response.data)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/login', data={
            'email': 'test_student@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        self.assert200(response)
        self.assertIn(b'Invalid email or password', response.data)
    
    def test_registration_success(self):
        """Test successful registration"""
        response = self.client.post('/register', data={
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new_user@example.com',
            'password': 'newuserpass',
            'confirm_password': 'newuserpass'
        }, follow_redirects=True)
        
        self.assert200(response)
        self.assertIn(b'Account created successfully', response.data)
        
        # Verify the user was created in the database
        new_user = User.query.filter_by(email='new_user@example.com').first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.first_name, 'New')
        self.assertEqual(new_user.last_name, 'User')
    
    def test_registration_duplicate_email(self):
        """Test registration with an already registered email"""
        response = self.client.post('/register', data={
            'first_name': 'Duplicate',
            'last_name': 'User',
            'email': 'test_student@example.com',  # Email already exists
            'password': 'duplicatepass',
            'confirm_password': 'duplicatepass'
        }, follow_redirects=True)
        
        self.assert200(response)
        self.assertIn(b'Email is already registered', response.data)
    
    def test_logout(self):
        """Test logout functionality"""
        # First login
        self.client.post('/login', data={
            'email': 'test_student@example.com',
            'password': 'teststudentpass'
        })
        
        # Then logout
        response = self.client.get('/logout', follow_redirects=True)
        self.assert200(response)
        self.assertIn(b'You have been logged out', response.data)

if __name__ == '__main__':
    unittest.main()