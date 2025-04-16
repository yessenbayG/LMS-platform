from flask import Flask
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from lms.utils.db import db
from lms.models.course import Course, Enrollment
from lms.models.user import User
from lms.models.message import Message

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    try:
        # Find users to test with
        admin = User.query.filter_by(email='admin@example.com').first()
        student = User.query.filter_by(email='student@example.com').first()
        
        if admin and student:
            print(f'Found admin (ID: {admin.id}) and student (ID: {student.id})')
            
            # Create test message from admin to student
            test_message = Message(
                sender_id=admin.id,
                recipient_id=student.id,
                content='This is a test message from admin to student'
            )
            db.session.add(test_message)
            
            # Create test message from student to admin
            test_message2 = Message(
                sender_id=student.id,
                recipient_id=admin.id,
                content='This is a test reply from student to admin'
            )
            db.session.add(test_message2)
            
            db.session.commit()
            print('Test messages created successfully')
            
            # Verify messages were created
            messages = Message.query.all()
            print(f'Total messages in database: {len(messages)}')
            
            # Get conversation
            conversation = Message.get_conversation(admin.id, student.id)
            print(f'Messages in conversation: {len(conversation)}')
            for msg in conversation:
                print(f'Message ID: {msg.id}, From: {"Admin" if msg.sender_id == admin.id else "Student"}, Content: {msg.content[:20]}...')
        else:
            print('Test users not found')
            if not admin:
                print('Admin user not found')
            if not student:
                print('Student user not found')
    except Exception as e:
        print(f'Error creating test messages: {str(e)}')
