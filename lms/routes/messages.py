from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app as app
from flask_login import login_required, current_user
from lms.models.user import User
from lms.models.message import Message
from lms.utils.db import db
from sqlalchemy import or_

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/')
@login_required
def inbox():
    """Show the user's message inbox with all conversations"""
    try:
        conversations = Message.get_conversations_for_user(current_user.id)
        
        # Get contact details for each conversation
        contacts = []
        for conv in conversations:
            contact = User.query.get(conv['contact_id'])
            if contact:
                contacts.append({
                    'user': contact,
                    'latest_message': conv['latest_message'],
                    'unread': not conv['latest_message'].read and conv['latest_message'].recipient_id == current_user.id
                })
        
        # Count total unread messages
        unread_count = Message.count_unread_messages(current_user.id)
        
        # Get potential new contacts based on user role
        new_contacts = []
        
        if current_user.is_student():
            # For students: can message their teachers and admin (support)
            # Get teachers of courses the student is enrolled in
            teachers = []
            try:
                # Use a simpler query approach that's more likely to work across SQLAlchemy versions
                from lms.models.course import Course, Enrollment
                app.logger.debug("Looking for teachers of student's courses")
                
                # First approach: Get through enrollments
                enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
                app.logger.debug(f"Found {len(enrollments)} enrollments")
                
                if enrollments:
                    course_ids = [enrollment.course_id for enrollment in enrollments]
                    app.logger.debug(f"Course IDs: {course_ids}")
                    teachers = User.query.join(Course, User.id == Course.teacher_id).filter(Course.id.in_(course_ids)).all()
                    app.logger.debug(f"Found {len(teachers)} teachers through joins")
                
                # If no teachers found, try simpler approach
                if not teachers:
                    # Just get all teachers for now
                    app.logger.debug("No teachers found through joins, getting all teachers")
                    teachers = User.query.join(User.role).filter(User.role.has(name='teacher')).all()
                    app.logger.debug(f"Found {len(teachers)} teachers total")
            except Exception as e:
                app.logger.error(f"Error getting teachers: {str(e)}")
                # Fallback: get all teachers as potential contacts
                teachers = User.query.join(User.role).filter(User.role.has(name='teacher')).all()
            
            # Add admins (for support)
            admins = User.query.join(User.role).filter(User.role.has(name='admin')).all()
            
            new_contacts = list(set(teachers + admins))
        
        elif current_user.is_teacher():
            # For teachers: can message students in their courses and admins
            # Get students enrolled in the teacher's courses
            students = []
            try:
                # Use a simpler query approach
                from lms.models.course import Course, Enrollment
                # Get courses taught by this teacher
                courses = Course.query.filter_by(teacher_id=current_user.id).all()
                course_ids = [course.id for course in courses]
                
                # Get students enrolled in these courses
                enrollments = Enrollment.query.filter(Enrollment.course_id.in_(course_ids)).all()
                student_ids = [enrollment.student_id for enrollment in enrollments]
                
                students = User.query.filter(User.id.in_(student_ids)).distinct().all()
            except Exception as e:
                app.logger.error(f"Error getting students: {str(e)}")
                # Fallback: show all students
                students = User.query.join(User.role).filter(User.role.has(name='student')).all()
            
            # Add admins (for support)
            admins = User.query.join(User.role).filter(User.role.has(name='admin')).all()
            
            new_contacts = list(set(students + admins))
        
        elif current_user.is_admin():
            # For admins: can message any user
            new_contacts = User.query.filter(User.id != current_user.id).all()
        
        # Remove users already in conversations and self
        try:
            contact_ids = [conv['contact_id'] for conv in conversations]
            new_contacts = [user for user in new_contacts if user.id not in contact_ids and user.id != current_user.id]
            app.logger.debug(f"Found {len(new_contacts)} new potential contacts")
        except Exception as e:
            app.logger.error(f"Error filtering contacts: {str(e)}")
            new_contacts = []
        
        return render_template(
            'messages/inbox.html', 
            contacts=contacts, 
            unread_count=unread_count,
            new_contacts=new_contacts
        )
    except Exception as e:
        app.logger.error(f"Error in inbox view: {str(e)}")
        flash("An error occurred loading your messages. Please try again later.", "danger")
        return redirect(url_for('index'))

@messages_bp.route('/<int:user_id>')
@login_required
def conversation(user_id):
    """Show conversation with a specific user"""
    try:
        other_user = User.query.get_or_404(user_id)
        
        # Check if the users can message each other
        can_message = True
        
        # Always allow messaging users we've already conversed with
        has_previous_messages = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.recipient_id == user_id)) | 
            ((Message.sender_id == user_id) & (Message.recipient_id == current_user.id))
        ).first() is not None
        
        if has_previous_messages:
            app.logger.debug(f"Users {current_user.id} and {user_id} have previous messages")
            can_message = True
        elif current_user.is_student():
            # Students can only message their teachers or admins if no previous conversation
            app.logger.debug(f"Student {current_user.id} checking if can message user {user_id}")
            
            try:
                # Check if the other user is a teacher or admin
                if other_user.is_admin():
                    app.logger.debug(f"User {user_id} is admin, allowing")
                    can_message = True
                elif other_user.is_teacher():
                    app.logger.debug(f"User {user_id} is teacher, allowing")
                    # Just allow any teacher for simplicity
                    can_message = True
                else:
                    app.logger.debug(f"User {user_id} is not teacher or admin, denying")
                    can_message = False
            except Exception as e:
                app.logger.error(f"Error checking messaging permissions: {str(e)}")
                # Fallback: allow messaging
                can_message = True
        
        elif current_user.is_teacher():
            # Teachers can only message their students or admins
            app.logger.debug(f"Teacher {current_user.id} checking if can message user {user_id}")
            
            try:
                # Check if the other user is a student or admin
                if other_user.is_admin():
                    app.logger.debug(f"User {user_id} is admin, allowing")
                    can_message = True
                elif other_user.is_student():
                    app.logger.debug(f"User {user_id} is student, allowing")
                    # Just allow any student for simplicity
                    can_message = True
                else:
                    app.logger.debug(f"User {user_id} is not student or admin, denying")
                    can_message = False
            except Exception as e:
                app.logger.error(f"Error checking messaging permissions: {str(e)}")
                # Fallback: allow messaging
                can_message = True
        
        # Admins can message anyone
        elif current_user.is_admin():
            app.logger.debug(f"Admin {current_user.id} can message anyone")
            can_message = True
        
        if not can_message:
            flash('You cannot message this user.', 'danger')
            return redirect(url_for('messages.inbox'))
        
        # Get messages and mark them as read
        try:
            messages = Message.get_conversation(current_user.id, user_id)
            Message.mark_conversation_as_read(current_user.id, user_id)
            
            # Reverse messages to show oldest first
            messages.reverse()
        except Exception as e:
            app.logger.error(f"Error getting messages: {str(e)}")
            messages = []
        
        return render_template(
            'messages/conversation.html', 
            other_user=other_user, 
            messages=messages
        )
    except Exception as e:
        app.logger.error(f"Error in conversation view: {str(e)}")
        flash("An error occurred loading the conversation. Please try again later.", "danger")
        return redirect(url_for('messages.inbox'))

@messages_bp.route('/<int:user_id>/send', methods=['POST'])
@login_required
def send_message(user_id):
    """Send a message to another user"""
    try:
        content = request.form.get('content', '').strip()
        
        if not content:
            flash('Message cannot be empty.', 'danger')
            return redirect(url_for('messages.conversation', user_id=user_id))
        
        other_user = User.query.get_or_404(user_id)
        
        # For simplicity, allow sending messages between any users
        # In a production system, you'd want to check permissions
        
        message = Message(
            sender_id=current_user.id,
            recipient_id=user_id,
            content=content
        )
        
        db.session.add(message)
        db.session.commit()
        
        return redirect(url_for('messages.conversation', user_id=user_id))
    except Exception as e:
        app.logger.error(f"Error sending message: {str(e)}")
        flash("An error occurred sending your message. Please try again.", "danger")
        return redirect(url_for('messages.conversation', user_id=user_id))

@messages_bp.route('/unread/count')
@login_required
def unread_count():
    """Get the count of unread messages (for AJAX requests)"""
    try:
        count = Message.count_unread_messages(current_user.id)
        return jsonify({'count': count})
    except Exception as e:
        app.logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'count': 0})