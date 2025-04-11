from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from lms.utils.db import db
from lms.utils.forms import (CourseCreationForm, MaterialForm, AssignmentForm, GradingForm,
                            ModuleForm, TestForm, QuestionForm, OptionForm)
from lms.models.user import User, Role
from lms.models.course import (Course, Category, Material, Assignment, Submission, Enrollment,
                              Module, Test, Question, QuestionOption, TestAttempt, TestAnswer, ModuleProgress)
from werkzeug.utils import secure_filename
import os
from functools import wraps
from datetime import datetime

teacher_bp = Blueprint('teacher', __name__)

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@teacher_bp.route('/dashboard')
@login_required
@teacher_required
def dashboard():
    # Get courses created by this teacher
    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    
    # Get statistics
    total_courses = len(courses)
    
    course_stats = []
    for course in courses:
        enrollments = Enrollment.query.filter_by(course_id=course.id).count()
        assignments = Assignment.query.filter_by(course_id=course.id).count()
        course_stats.append({
            'id': course.id,
            'title': course.title,
            'enrollments': enrollments,
            'assignments': assignments
        })
    
    return render_template('teacher/dashboard.html', 
                           total_courses=total_courses, 
                           course_stats=course_stats)

@teacher_bp.route('/courses/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_course():
    form = CourseCreationForm()
    
    # Get available categories for the dropdown
    categories = Category.query.all()
    form.category.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        image_path = None
        
        # Handle image upload
        if form.course_image.data:
            image = form.course_image.data
            image_filename = secure_filename(image.filename)
            # Create a unique filename to avoid collisions
            unique_filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{image_filename}"
            image_path = os.path.join('uploads', 'course_images', unique_filename)
            
            # Make sure the directory exists
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'course_images')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save the file
            image.save(os.path.join(upload_dir, unique_filename))
        
        course = Course(
            title=form.title.data,
            description=form.description.data,
            category_id=form.category.data,
            teacher_id=current_user.id,
            image_path=image_path
        )
        db.session.add(course)
        db.session.commit()
        flash('Course created successfully!', 'success')
        
        # Redirect to add modules instead of directly to course content
        return redirect(url_for('teacher.manage_modules', course_id=course.id))
    
    return render_template('teacher/create_course.html', form=form)

@teacher_bp.route('/courses/<int:course_id>/content')
@login_required
@teacher_required
def add_course_content(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    material_form = MaterialForm()
    assignment_form = AssignmentForm()
    
    return render_template('teacher/course_content.html', 
                           course=course, 
                           material_form=material_form, 
                           assignment_form=assignment_form)

def save_file(file):
    filename = secure_filename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return os.path.join('uploads', filename)

@teacher_bp.route('/courses/<int:course_id>/materials/add', methods=['POST'])
@login_required
@teacher_required
def add_material(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = MaterialForm()
    if form.validate_on_submit():
        file_path = None
        content = form.content.data
        
        if form.content_type.data == 'file' and form.file.data:
            file_path = save_file(form.file.data)
        
        material = Material(
            title=form.title.data,
            content_type=form.content_type.data,
            content=content,
            file_path=file_path,
            course_id=course.id
        )
        db.session.add(material)
        db.session.commit()
        flash('Material added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.add_course_content', course_id=course.id))

@teacher_bp.route('/courses/<int:course_id>/assignments/add', methods=['POST'])
@login_required
@teacher_required
def add_assignment(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = AssignmentForm()
    if form.validate_on_submit():
        assignment = Assignment(
            title=form.title.data,
            description=form.description.data,
            course_id=course.id
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Assignment added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.add_course_content', course_id=course.id))

@teacher_bp.route('/courses/<int:course_id>/students')
@login_required
@teacher_required
def course_students(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to view this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    enrolled_students = [enrollment.student for enrollment in enrollments]
    
    return render_template('teacher/course_students.html', 
                           course=course, 
                           students=enrolled_students)

@teacher_bp.route('/assignments/<int:assignment_id>/submissions')
@login_required
@teacher_required
def assignment_submissions(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to view these submissions.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    
    return render_template('teacher/submissions.html', 
                           course=course, 
                           assignment=assignment, 
                           submissions=submissions)

@teacher_bp.route('/submissions/<int:submission_id>/grade', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_submission(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    assignment = submission.assignment
    course = assignment.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to grade this submission.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = GradingForm()
    
    if form.validate_on_submit():
        submission.grade = form.grade.data
        submission.feedback = form.feedback.data
        submission.graded_at = datetime.utcnow()
        db.session.commit()
        
        # Update overall student grade for the course
        update_student_course_grade(submission.student_id, course.id)
        
        flash('Submission graded successfully!', 'success')
        return redirect(url_for('teacher.assignment_submissions', assignment_id=assignment.id))
    elif request.method == 'GET':
        if submission.grade is not None:
            form.grade.data = submission.grade
            form.feedback.data = submission.feedback
    
    return render_template('teacher/grade_submission.html', 
                           form=form, 
                           submission=submission, 
                           assignment=assignment, 
                           student=submission.student)

def update_student_course_grade(student_id, course_id):
    """Calculate and update the overall grade for a student in a course"""
    # Get all assignments for this course
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    
    if not assignments:
        return  # No assignments to grade
    
    total_points = 0
    earned_points = 0
    
    # Calculate points from assignments
    for assignment in assignments:
        submission = Submission.query.filter_by(
            assignment_id=assignment.id, 
            student_id=student_id
        ).first()
        
        # If the submission exists and has been graded
        if submission and submission.grade is not None:
            # Assume all assignments are worth 100 points
            total_points += 100
            earned_points += submission.grade
    
    # Get test attempts
    module_ids = [module.id for module in Module.query.filter_by(course_id=course_id).all()]
    
    if module_ids:
        tests = Test.query.filter(Test.module_id.in_(module_ids)).all()
        
        for test in tests:
            # Get the best attempt for this test
            best_attempt = TestAttempt.query.filter_by(
                test_id=test.id,
                student_id=student_id
            ).order_by(TestAttempt.score.desc()).first()
            
            if best_attempt and best_attempt.score is not None:
                total_points += 100
                earned_points += best_attempt.score
    
    # Calculate overall grade if there are points possible
    if total_points > 0:
        overall_grade = (earned_points / total_points) * 100
        
        # Update the enrollment record
        enrollment = Enrollment.query.filter_by(
            student_id=student_id,
            course_id=course_id
        ).first()
        
        if enrollment:
            enrollment.overall_grade = overall_grade
            db.session.commit()

# Module management routes
@teacher_bp.route('/courses/<int:course_id>/modules')
@login_required
@teacher_required
def manage_modules(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to manage this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    modules = Module.query.filter_by(course_id=course.id).order_by(Module.order).all()
    form = ModuleForm()
    
    return render_template('teacher/manage_modules.html',
                          course=course,
                          modules=modules,
                          form=form)

@teacher_bp.route('/courses/<int:course_id>/modules/add', methods=['POST'])
@login_required
@teacher_required
def add_module(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to manage this course.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = ModuleForm()
    if form.validate_on_submit():
        module = Module(
            title=form.title.data,
            description=form.description.data,
            order=form.order.data,
            course_id=course.id
        )
        db.session.add(module)
        db.session.commit()
        flash('Module added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.manage_modules', course_id=course.id))

@teacher_bp.route('/modules/<int:module_id>')
@login_required
@teacher_required
def view_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to view this module.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    materials = Material.query.filter_by(module_id=module.id).order_by(Material.order).all()
    tests = Test.query.filter_by(module_id=module.id).all()
    
    material_form = MaterialForm()
    test_form = TestForm()
    
    return render_template('teacher/view_module.html',
                          course=course,
                          module=module,
                          materials=materials,
                          tests=tests,
                          material_form=material_form,
                          test_form=test_form)

@teacher_bp.route('/modules/<int:module_id>/materials/add', methods=['POST'])
@login_required
@teacher_required
def add_module_material(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this module.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = MaterialForm()
    if form.validate_on_submit():
        file_path = None
        content = form.content.data
        
        if form.content_type.data == 'file' and form.file.data:
            file_path = save_file(form.file.data)
        
        # Get the highest order number and add 1
        highest_order = db.session.query(db.func.max(Material.order)).filter_by(module_id=module.id).scalar() or 0
        
        material = Material(
            title=form.title.data,
            content_type=form.content_type.data,
            content=content,
            file_path=file_path,
            course_id=course.id,
            module_id=module.id,
            order=highest_order + 1
        )
        db.session.add(material)
        db.session.commit()
        flash('Material added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.view_module', module_id=module.id))

# Test management routes
@teacher_bp.route('/modules/<int:module_id>/tests/add', methods=['POST'])
@login_required
@teacher_required
def add_test(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this module.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = TestForm()
    if form.validate_on_submit():
        test = Test(
            title=form.title.data,
            description=form.description.data,
            passing_score=form.passing_score.data,
            module_id=module.id
        )
        db.session.add(test)
        db.session.commit()
        flash('Test added successfully!', 'success')
        return redirect(url_for('teacher.edit_test', test_id=test.id))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.view_module', module_id=module.id))

@teacher_bp.route('/tests/<int:test_id>/edit')
@login_required
@teacher_required
def edit_test(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this test.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    questions = Question.query.filter_by(test_id=test.id).all()
    question_form = QuestionForm()
    
    return render_template('teacher/edit_test.html',
                          course=course,
                          module=module,
                          test=test,
                          questions=questions,
                          question_form=question_form)

@teacher_bp.route('/tests/<int:test_id>/questions/add', methods=['POST'])
@login_required
@teacher_required
def add_question(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this test.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = QuestionForm()
    if form.validate_on_submit():
        question = Question(
            question_text=form.question_text.data,
            question_type=form.question_type.data,
            points=form.points.data,
            test_id=test.id
        )
        db.session.add(question)
        db.session.commit()
        
        # If it's true/false, automatically add Yes/No options
        if form.question_type.data == 'true_false':
            true_option = QuestionOption(
                option_text='True',
                is_correct=True,
                question_id=question.id
            )
            false_option = QuestionOption(
                option_text='False',
                is_correct=False,
                question_id=question.id
            )
            db.session.add_all([true_option, false_option])
            db.session.commit()
            flash('True/False question added successfully!', 'success')
        else:
            flash('Question added successfully! Now add options for this question.', 'success')
            return redirect(url_for('teacher.edit_question', question_id=question.id))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.edit_test', test_id=test.id))

@teacher_bp.route('/questions/<int:question_id>/edit')
@login_required
@teacher_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    test = question.test
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    options = QuestionOption.query.filter_by(question_id=question.id).all()
    option_form = OptionForm()
    
    return render_template('teacher/edit_question.html',
                          course=course,
                          module=module,
                          test=test,
                          question=question,
                          options=options,
                          option_form=option_form)

@teacher_bp.route('/questions/<int:question_id>/options/add', methods=['POST'])
@login_required
@teacher_required
def add_option(question_id):
    question = Question.query.get_or_404(question_id)
    test = question.test
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to edit this question.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    form = OptionForm()
    if form.validate_on_submit():
        option = QuestionOption(
            option_text=form.option_text.data,
            is_correct=form.is_correct.data,
            question_id=question.id
        )
        db.session.add(option)
        db.session.commit()
        flash('Option added successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('teacher.edit_question', question_id=question.id))

@teacher_bp.route('/tests/<int:test_id>/results')
@login_required
@teacher_required
def test_results(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Ensure the teacher is the owner of the course
    if course.teacher_id != current_user.id:
        flash('You do not have permission to view these results.', 'danger')
        return redirect(url_for('teacher.dashboard'))
    
    # Get all attempts for this test grouped by student
    attempts = db.session.query(
        User, 
        db.func.count(TestAttempt.id).label('num_attempts'),
        db.func.max(TestAttempt.score).label('highest_score')
    ).join(
        TestAttempt, User.id == TestAttempt.student_id
    ).filter(
        TestAttempt.test_id == test.id
    ).group_by(
        User.id
    ).all()
    
    return render_template('teacher/test_results.html',
                          course=course,
                          module=module,
                          test=test,
                          attempts=attempts)