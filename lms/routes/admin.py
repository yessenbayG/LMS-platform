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
    
    # Get payment stats
    pending_teacher_payments = Course.query.filter(
        Course.payment_receipt_path != None,
        Course.payment_verified == False
    ).count()
    
    pending_student_payments = Enrollment.query.filter(
        Enrollment.payment_receipt_path != None,
        Enrollment.payment_verified == False
    ).count()
    
    total_pending_payments = pending_teacher_payments + pending_student_payments
    
    stats = {
        'students': total_students,
        'teachers': total_teachers,
        'courses': total_courses,
        'enrollments': total_enrollments,
        'pending_payments': total_pending_payments,
        'pending_teacher_payments': pending_teacher_payments,
        'pending_student_payments': pending_student_payments
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/teachers')
@login_required
@admin_required
def manage_teachers():
    # Get all teachers
    teachers = User.query.join(Role).filter(Role.name == 'teacher').all()
    
    # Get students who have applied to become teachers (have certificate pending verification)
    teacher_applicants = User.query.join(Role).filter(
        Role.name == 'student',
        User.certificate_path != None,
        User.certificate_verified == False
    ).all()
    
    return render_template('admin/teachers.html', teachers=teachers, teacher_applicants=teacher_applicants)

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
    
    # Also get courses with pending payments
    payment_pending_courses = Course.query.filter(
        Course.payment_receipt_path != None,
        Course.payment_verified == False
    ).all()
    
    return render_template('admin/courses.html', 
                          pending_courses=pending_courses,
                          approved_courses=approved_courses,
                          payment_pending_courses=payment_pending_courses)

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

@admin_bp.route('/courses/delete/<int:course_id>', methods=['GET', 'POST'])
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
    
    # Check if there's a payment receipt but it hasn't been verified
    if course.payment_receipt_path and not course.payment_verified:
        flash(f'Please verify the payment receipt for "{course.title}" before approving the course.', 'warning')
        return redirect(url_for('admin.manage_courses'))
    
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

@admin_bp.route('/students/approve-application/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_student_application(user_id):
    student = User.query.get_or_404(user_id)
    
    # Check if the user is a student with a certificate
    if not student.is_student() or not student.certificate_path:
        flash('Invalid student application.', 'danger')
        return redirect(url_for('admin.manage_teachers'))
    
    # Get teacher role
    teacher_role = Role.query.filter_by(name='teacher').first()
    if not teacher_role:
        flash('Teacher role not found in the system.', 'danger')
        return redirect(url_for('admin.manage_teachers'))
    
    # Convert student to teacher
    student.role_id = teacher_role.id
    student.certificate_verified = True
    db.session.commit()
    
    flash(f'{student.get_full_name()} has been approved as a teacher!', 'success')
    return redirect(url_for('admin.manage_teachers'))

@admin_bp.route('/students/reject-application/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reject_student_application(user_id):
    student = User.query.get_or_404(user_id)
    
    # Check if the user is a student with a certificate
    if not student.is_student() or not student.certificate_path:
        flash('Invalid student application.', 'danger')
        return redirect(url_for('admin.manage_teachers'))
    
    # Reject application (mark as not verified, but keep the certificate record)
    student.certificate_verified = False
    db.session.commit()
    
    flash(f'Teacher application from {student.get_full_name()} has been rejected.', 'info')
    return redirect(url_for('admin.manage_teachers'))

@admin_bp.route('/debug/create-subscription-plans')
# Debug purposes only - no auth required
def debug_create_subscription_plans():
    """Debug route to create subscription plans"""
    try:
        from lms.models.course import TeacherSubscriptionPlan
        
        # Clear existing plans
        TeacherSubscriptionPlan.query.delete()
        
        # Create subscription plans
        plans = [
            TeacherSubscriptionPlan(name="Standard - Up to 10 students", max_students=10, price_per_month=20000, description="Basic plan for small classes"),
            TeacherSubscriptionPlan(name="Pro - Up to 30 students", max_students=30, price_per_month=35000, description="Professional plan for medium classes"),
            TeacherSubscriptionPlan(name="Premium - Up to 100 students", max_students=100, price_per_month=70000, description="Premium plan for large classes"),
            TeacherSubscriptionPlan(name="Enterprise - Unlimited students", max_students=10000, price_per_month=100000, description="Enterprise plan for unlimited students")
        ]
        
        for plan in plans:
            db.session.add(plan)
        
        db.session.commit()
        
        # Get all subscription plans to verify
        all_plans = TeacherSubscriptionPlan.query.all()
        plan_info = "\n".join([f"ID: {p.id}, Name: {p.name}, Max Students: {p.max_students}, Price: {p.price_per_month} KZT" for p in all_plans])
        
        return f"Successfully created {len(plans)} subscription plans:<br><pre>{plan_info}</pre>"
    except Exception as e:
        db.session.rollback()
        return f"Error creating subscription plans: {str(e)}"

@admin_bp.route('/payments')
@login_required
@admin_required
def manage_payments():
    # Get courses with unverified teacher payments
    teacher_payments = Course.query.filter(
        Course.payment_receipt_path != None,
        Course.payment_verified == False
    ).all()
    
    # Get enrollment payments that need verification
    student_payments = Enrollment.query.filter(
        Enrollment.payment_receipt_path != None,
        Enrollment.payment_verified == False
    ).all()
    
    return render_template('admin/payments.html',
                          teacher_payments=teacher_payments,
                          student_payments=student_payments)

@admin_bp.route('/payments/verify-teacher/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def verify_teacher_payment(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify teacher's payment for this course
    course.payment_verified = True
    db.session.commit()
    
    flash(f'Payment for course "{course.title}" by {course.teacher.get_full_name()} has been verified.', 'success')
    return redirect(url_for('admin.manage_payments'))

@admin_bp.route('/payments/reject-teacher/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def reject_teacher_payment(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Reject teacher's payment (keep records for reference)
    course.payment_verified = False
    db.session.commit()
    
    flash(f'Payment for course "{course.title}" by {course.teacher.get_full_name()} has been rejected.', 'warning')
    return redirect(url_for('admin.manage_payments'))

@admin_bp.route('/payments/verify-student/<int:enrollment_id>', methods=['POST'])
@login_required
@admin_required
def verify_student_payment(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    student = enrollment.student
    course = enrollment.course
    
    # Verify student's payment for this enrollment
    enrollment.payment_verified = True
    db.session.commit()
    
    flash(f'Payment by {student.get_full_name()} for course "{course.title}" has been verified.', 'success')
    return redirect(url_for('admin.manage_payments'))

@admin_bp.route('/payments/reject-student/<int:enrollment_id>', methods=['POST'])
@login_required
@admin_required
def reject_student_payment(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    student = enrollment.student
    course = enrollment.course
    
    # Reject student's payment (keep records for reference)
    enrollment.payment_verified = False
    db.session.commit()
    
    flash(f'Payment by {student.get_full_name()} for course "{course.title}" has been rejected.', 'warning')
    return redirect(url_for('admin.manage_payments'))