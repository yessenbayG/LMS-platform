from flask import Blueprint, render_template, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from lms.models.course import Course, Material, Assignment
import os

course_bp = Blueprint('course', __name__)

@course_bp.route('/')
@login_required
def list_courses():
    if current_user.is_admin():
        courses = Course.query.all()
    elif current_user.is_teacher():
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
    else:  # Student
        return redirect(url_for('student.browse_courses'))
    
    return render_template('courses/list.html', courses=courses)

@course_bp.route('/<int:course_id>')
@login_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    if current_user.is_student():
        return redirect(url_for('student.view_course', course_id=course.id))
    
    materials = Material.query.filter_by(course_id=course.id).all()
    assignments = Assignment.query.filter_by(course_id=course.id).all()
    
    return render_template('courses/view.html', 
                          course=course, 
                          materials=materials, 
                          assignments=assignments)

@course_bp.route('/material/<int:material_id>')
@login_required
def view_material(material_id):
    material = Material.query.get_or_404(material_id)
    course = material.course
    
    # Check permissions: admin, course teacher, or enrolled student
    if not (current_user.is_admin() or 
            (current_user.is_teacher() and course.teacher_id == current_user.id) or 
            (current_user.is_student() and any(e.student_id == current_user.id for e in course.enrollments))):
        flash('You do not have permission to access this material.', 'danger')
        return redirect(url_for('course.list_courses'))
    
    return render_template('courses/material.html', course=course, material=material)

@course_bp.route('/uploads/<path:filename>')
@login_required
def download_file(filename):
    uploads_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], '')
    directory = os.path.dirname(uploads_folder)
    filename = os.path.basename(filename)
    return send_from_directory(directory, filename)