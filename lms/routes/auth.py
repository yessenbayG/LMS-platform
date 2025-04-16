from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from lms.utils.db import db
from lms.utils.forms import LoginForm, RegistrationForm, ProfileUpdateForm, PasswordChangeForm
from lms.models.user import User, Role
from werkzeug.security import check_password_hash, generate_password_hash
import logging

# Set up logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_teacher():
            return redirect(url_for('teacher.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
    
    form = LoginForm()
    
    # Only process if form was submitted and is valid
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        # Use SQLAlchemy ORM for authentication
        user = User.query.filter_by(email=email).first()
        
        if user:
            logger.info(f"Found user: {user.email}, role: {user.role.name if user.role else None}, active: {user.is_active}")
            
            # Verify password using the verify_password method
            password_match = user.verify_password(password)
            logger.info(f"Password match: {password_match}")
            
            if password_match and user.is_active:
                # Login the user with Flask-Login
                login_user(user)
                logger.info(f"User {user.email} logged in successfully")
                
                # Redirect based on role
                if user.is_admin():
                    return redirect(url_for('admin.dashboard'))
                elif user.is_teacher():
                    return redirect(url_for('teacher.dashboard'))
                else:
                    return redirect(url_for('student.dashboard'))
            else:
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                else:
                    flash('Invalid email or password.', 'danger')
        else:
            logger.warning(f"No user found with email: {email}")
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # All registrations are for students only
            student_role = Role.query.filter_by(name='student').first()
            
            if not student_role:
                logger.error("Student role not found in database")
                flash('Registration failed. Please contact support.', 'danger')
                return render_template('auth/register.html', form=form)
            
            role_id = student_role.id
            account_type = "Student"
                
            user = User(
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                email=form.email.data,
                password=form.password.data,
                role_id=role_id
            )
            db.session.add(user)
            db.session.commit()
            flash(f'{account_type} account created successfully! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during registration: {str(e)}")
            flash('Registration failed. Please try again later.', 'danger')
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm(original_email=current_user.email)
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('auth.profile'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    
    return render_template('auth/profile.html', form=form)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordChangeForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.current_password.data):
            current_user.password = form.new_password.data
            db.session.commit()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Current password is incorrect.', 'danger')
    
    return render_template('auth/change_password.html', form=form)