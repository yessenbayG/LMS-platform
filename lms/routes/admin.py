from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from lms.utils.db import db
from lms.utils.forms import TeacherCreationForm, CourseCreationForm, ModuleForm, AdminCreationForm
from lms.models.user import User, Role
from werkzeug.security import generate_password_hash
from datetime import datetime
from lms.models.course import (Course, Category, Enrollment, Module, Material, Test,
                               Assignment, Question, QuestionOption)
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get statistics for dashboard
    total_students = User.query.join(Role).filter(Role.name == 'student').count()
    total_teachers = User.query.join(Role).filter(Role.name == 'teacher').count()
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()
    
    stats = {
        'students': total_students,
        'teachers': total_teachers,
        'courses': total_courses,
        'enrollments': total_enrollments
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/teachers')
@login_required
@admin_required
def manage_teachers():
    teachers = User.query.join(Role).filter(Role.name == 'teacher').all()
    return render_template('admin/teachers.html', teachers=teachers)

@admin_bp.route('/teachers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_teacher():
    form = TeacherCreationForm()
    if form.validate_on_submit():
        teacher_role = Role.query.filter_by(name='teacher').first()
        teacher = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=form.password.data,
            role_id=teacher_role.id
        )
        db.session.add(teacher)
        db.session.commit()
        flash('Teacher account created successfully!', 'success')
        return redirect(url_for('admin.manage_teachers'))
    
    return render_template('admin/create_teacher.html', form=form)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    role_filter = request.args.get('role', 'all')
    
    if role_filter == 'student':
        users = User.query.join(Role).filter(Role.name == 'student').all()
    elif role_filter == 'teacher':
        users = User.query.join(Role).filter(Role.name == 'teacher').all()
    elif role_filter == 'admin':
        users = User.query.join(Role).filter(Role.name == 'admin').all()
    else:
        users = User.query.all()
    
    return render_template('admin/users.html', users=users, current_filter=role_filter)

@admin_bp.route('/admins/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_admin():
    form = AdminCreationForm()
    if form.validate_on_submit():
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            flash('Admin role not found in database. Please contact the system administrator.', 'danger')
            return render_template('admin/create_admin.html', form=form)
        
        # Create new admin user
        admin = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            role_id=admin_role.id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        admin.password_hash = generate_password_hash(form.password.data)
        
        try:
            db.session.add(admin)
            db.session.commit()
            flash('Administrator account created successfully!', 'success')
            return redirect(url_for('admin.manage_users', role='admin'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating administrator account: {str(e)}', 'danger')
    
    return render_template('admin/create_admin.html', form=form)

@admin_bp.route('/users/toggle/<int:user_id>')
@login_required
@admin_required
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating own account
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.email} has been {status}.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/courses')
@login_required
@admin_required
def manage_courses():
    pending_courses = Course.query.filter_by(is_approved=False).all()
    approved_courses = Course.query.filter_by(is_approved=True).all()
    return render_template('admin/courses.html', 
                          pending_courses=pending_courses,
                          approved_courses=approved_courses)

@admin_bp.route('/courses/edit/<int:course_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    form = CourseCreationForm(obj=course)
    
    # Get available categories for the dropdown
    categories = Category.query.all()
    form.category.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        # Handle image upload
        if form.course_image.data:
            image = form.course_image.data
            image_filename = secure_filename(image.filename)
            # Create a unique filename to avoid collisions
            unique_filename = f"admin_{int(datetime.utcnow().timestamp())}_{image_filename}"
            image_path = os.path.join('uploads', 'course_images', unique_filename)
            
            # Make sure the directory exists
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'course_images')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save the file
            image.save(os.path.join(upload_dir, unique_filename))
            
            # Update the course image path
            course.image_path = image_path
            
        # Update other fields
        course.title = form.title.data
        course.description = form.description.data
        course.category_id = form.category.data
        
        db.session.commit()
        flash('Course updated successfully!', 'success')
        return redirect(url_for('admin.manage_courses'))
    
    return render_template('admin/edit_course.html', form=form, course=course)

@admin_bp.route('/courses/modules/<int:course_id>')
@login_required
@admin_required
def manage_course_modules(course_id):
    course = Course.query.get_or_404(course_id)
    modules = Module.query.filter_by(course_id=course.id).order_by(Module.order).all()
    
    # For each module, get the number of materials and tests
    module_data = []
    for module in modules:
        material_count = Material.query.filter_by(module_id=module.id).count()
        test_count = Test.query.filter_by(module_id=module.id).count()
        
        module_data.append({
            'module': module,
            'material_count': material_count,
            'test_count': test_count
        })
    
    return render_template('admin/course_modules.html', 
                          course=course, 
                          module_data=module_data)

@admin_bp.route('/modules/edit/<int:module_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    form = ModuleForm(obj=module)
    
    if form.validate_on_submit():
        module.title = form.title.data
        module.description = form.description.data
        module.order = form.order.data
        
        db.session.commit()
        flash('Module updated successfully!', 'success')
        return redirect(url_for('admin.manage_course_modules', course_id=course.id))
    
    return render_template('admin/edit_module.html', 
                          form=form, 
                          module=module, 
                          course=course)

@admin_bp.route('/courses/delete/<int:course_id>')
@login_required
@admin_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Delete the course and all related data
    db.session.delete(course)
    db.session.commit()
    
    flash(f'Course "{course.title}" has been deleted.', 'success')
    return redirect(url_for('admin.manage_courses'))

@admin_bp.route('/courses/approve/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def approve_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Approve the course
    course.is_approved = True
    db.session.commit()
    
    flash(f'Course "{course.title}" has been approved.', 'success')
    return redirect(url_for('admin.manage_courses'))

@admin_bp.route('/teachers/verify-certificate/<int:user_id>')
@login_required
@admin_required
def verify_certificate(user_id):
    teacher = User.query.get_or_404(user_id)
    
    # Check if the user is a teacher and has a certificate to verify
    if not teacher.is_teacher() or not teacher.certificate_path:
        flash('Invalid teacher or no certificate found.', 'danger')
        return redirect(url_for('admin.manage_teachers'))
    
    # Verify the certificate
    teacher.certificate_verified = True
    db.session.commit()
    
    flash(f'Certificate for {teacher.get_full_name()} has been verified.', 'success')
    return redirect(url_for('admin.manage_teachers'))

@admin_bp.route('/teachers/unverify-certificate/<int:user_id>')
@login_required
@admin_required
def unverify_certificate(user_id):
    teacher = User.query.get_or_404(user_id)
    
    # Check if the user is a teacher
    if not teacher.is_teacher():
        flash('Invalid teacher account.', 'danger')
        return redirect(url_for('admin.manage_teachers'))
    
    # Unverify the certificate
    teacher.certificate_verified = False
    db.session.commit()
    
    flash(f'Certificate verification for {teacher.get_full_name()} has been revoked.', 'success')
    return redirect(url_for('admin.manage_teachers'))