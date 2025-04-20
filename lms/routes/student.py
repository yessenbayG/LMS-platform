from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from lms.utils.db import db
from lms.utils.forms import SubmissionForm, TestAttemptForm, CertificateForm
from lms.models.course import (Course, Material, Assignment, Submission, Enrollment, 
                              Module, Test, Question, QuestionOption, TestAttempt, 
                              TestAnswer, ModuleProgress, Wishlist)
from lms.models.user import User, Role
from datetime import datetime
import json
from werkzeug.utils import secure_filename
import os
from functools import wraps

student_bp = Blueprint('student', __name__)

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    # Get courses this student is enrolled in
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    enrolled_courses = [enrollment.course for enrollment in enrollments]
    
    # Get statistics
    total_courses = len(enrolled_courses)
    
    # Get assignment statistics and progress
    course_stats = []
    for course in enrolled_courses:
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        total_assignments = len(assignments)
        
        completed_assignments = 0
        for assignment in assignments:
            submission = Submission.query.filter_by(
                assignment_id=assignment.id,
                student_id=current_user.id
            ).first()
            if submission:
                completed_assignments += 1
        
        if total_assignments > 0:
            progress = (completed_assignments / total_assignments) * 100
        else:
            progress = 100  # No assignments means 100% complete
        
        course_stats.append({
            'id': course.id,
            'title': course.title,
            'teacher': course.teacher.get_full_name(),
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments,
            'progress': progress
        })
    
    return render_template('student/dashboard.html', 
                           total_courses=total_courses,
                           course_stats=course_stats)

@student_bp.route('/courses')
@login_required
@student_required
def browse_courses():
    # Get search parameters
    search_query = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int)
    sort_by = request.args.get('sort_by', 'popular')  # Default sort by popularity
    
    # Base query for available courses (active and approved)
    query = Course.query.filter_by(is_active=True, is_approved=True)
    
    # Apply search filters
    if search_query:
        query = query.filter(Course.title.ilike(f'%{search_query}%'))
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Get the filtered courses
    courses = query.all()
    
    # Sort the courses
    if sort_by == 'newest':
        courses = sorted(courses, key=lambda c: c.created_at, reverse=True)
    elif sort_by == 'title':
        courses = sorted(courses, key=lambda c: c.title.lower())
    else:  # Default: sort by popularity (enrollment count)
        courses = sorted(courses, key=lambda c: c.enrollment_count, reverse=True)
    
    # Get all categories for the filter dropdown
    categories = db.session.query(db.distinct(Course.category_id)).filter_by(is_active=True, is_approved=True).all()
    category_list = []
    for cat_id in categories:
        if cat_id[0]:  # Skip None values
            # Use query.get instead of get_or_404
            from lms.models.course import Category
            category = Category.query.get(cat_id[0])
            if category:
                category_list.append(category)
    
    # Get courses this student is already enrolled in
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    enrolled_course_ids = [enrollment.course_id for enrollment in enrollments]
    
    # Get wishlist items
    wishlist_items = Wishlist.query.filter_by(student_id=current_user.id).all()
    wishlist_course_ids = [item.course_id for item in wishlist_items]
    
    # Get the count of students enrolled in each course for display
    course_stats = {}
    for course in courses:
        course_stats[course.id] = {
            'enrollment_count': course.enrollment_count
        }
    
    return render_template('student/browse_courses.html', 
                          courses=courses, 
                          enrolled_course_ids=enrolled_course_ids,
                          wishlist_course_ids=wishlist_course_ids,
                          categories=category_list,
                          search_query=search_query,
                          selected_category=category_id,
                          sort_by=sort_by,
                          course_stats=course_stats)

@student_bp.route('/courses/<int:course_id>')
@login_required
@student_required
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if course is active
    if not course.is_active:
        # If student is not enrolled, don't show inactive courses
        enrollment = Enrollment.query.filter_by(
            student_id=current_user.id,
            course_id=course.id
        ).first()
        
        if not enrollment:
            flash('This course is not currently available.', 'warning')
            return redirect(url_for('student.browse_courses'))
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    # Check if in wishlist
    wishlist_item = Wishlist.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    materials = Material.query.filter_by(course_id=course.id).all()
    assignments = Assignment.query.filter_by(course_id=course.id).all()
    
    # Check which assignments have been submitted
    submitted_assignments = []
    for assignment in assignments:
        submission = Submission.query.filter_by(
            assignment_id=assignment.id,
            student_id=current_user.id
        ).first()
        if submission:
            submitted_assignments.append(assignment.id)
    
    return render_template('student/view_course.html', 
                           course=course, 
                           enrolled=enrollment is not None,
                           in_wishlist=wishlist_item is not None,
                           materials=materials, 
                           assignments=assignments,
                           submitted_assignments=submitted_assignments)

@student_bp.route('/courses/<int:course_id>/enroll', methods=['GET', 'POST'])
@login_required
@student_required
def enroll_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if course is active and approved
    if not course.is_active or not course.is_approved:
        flash('This course is not currently available for enrollment.', 'warning')
        return redirect(url_for('student.browse_courses'))
    
    # Check if course has reached capacity
    if course.is_at_capacity:
        flash('This course has reached its maximum student capacity. Please try again later or contact the teacher.', 'warning')
        return redirect(url_for('student.view_course', course_id=course.id))
    
    # Check if already enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if enrollment:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('student.view_course', course_id=course.id))
    
    # Handle enrollment with payment
    from lms.utils.forms import EnrollmentForm
    form = EnrollmentForm()
    
    if request.method == 'GET':
        # Show enrollment form with payment upload
        return render_template('student/enroll_course.html', 
                              course=course, 
                              form=form)
    
    # Handle form submission
    if form.validate_on_submit():
        payment_receipt_path = None
        
        # Handle payment receipt upload
        if form.payment_receipt.data:
            receipt = form.payment_receipt.data
            receipt_filename = secure_filename(receipt.filename)
            # Create a unique filename
            unique_receipt_name = f"student_{current_user.id}_{int(datetime.utcnow().timestamp())}_{receipt_filename}"
            payment_receipt_path = os.path.join('uploads', 'payment_receipts', unique_receipt_name)
            
            # Make sure the directory exists
            receipt_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payment_receipts')
            os.makedirs(receipt_dir, exist_ok=True)
            
            # Save the file
            receipt.save(os.path.join(receipt_dir, unique_receipt_name))
        
        # Create enrollment with payment information
        enrollment = Enrollment(
            student_id=current_user.id,
            course_id=course.id,
            payment_receipt_path=payment_receipt_path,
            payment_amount=course.enrollment_price,
            payment_verified=False,  # Payment needs to be verified by admin
            payment_date=datetime.utcnow()
        )
        db.session.add(enrollment)
        db.session.commit()
        
        flash('Your enrollment request has been submitted with payment receipt. You will have full access to the course after payment verification.', 'success')
        return redirect(url_for('student.view_course', course_id=course.id))
    
    # If form validation failed
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return render_template('student/enroll_course.html', 
                          course=course, 
                          form=form)

@student_bp.route('/courses/<int:course_id>/unenroll')
@login_required
@student_required
def unenroll_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
        flash('You have successfully unenrolled from this course.', 'success')
    else:
        flash('You are not enrolled in this course.', 'info')
    
    return redirect(url_for('student.browse_courses'))

@student_bp.route('/courses/<int:course_id>/wishlist/add')
@login_required
@student_required
def add_to_wishlist(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if already in wishlist
    wishlist_item = Wishlist.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if wishlist_item:
        flash('This course is already in your wishlist.', 'info')
    else:
        wishlist_item = Wishlist(
            student_id=current_user.id,
            course_id=course.id
        )
        db.session.add(wishlist_item)
        db.session.commit()
        flash('Course added to your wishlist!', 'success')
    
    return redirect(url_for('student.view_course', course_id=course.id))

@student_bp.route('/courses/<int:course_id>/wishlist/remove')
@login_required
@student_required
def remove_from_wishlist(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if in wishlist
    wishlist_item = Wishlist.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()
        flash('Course removed from your wishlist.', 'success')
    else:
        flash('This course is not in your wishlist.', 'info')
    
    return redirect(url_for('student.view_course', course_id=course.id))

@student_bp.route('/my-wishlist')
@login_required
@student_required
def view_wishlist():
    # Get all wishlist items
    wishlist_items = Wishlist.query.filter_by(student_id=current_user.id).all()
    wishlist_courses = [item.course for item in wishlist_items]
    
    return render_template('student/wishlist.html', courses=wishlist_courses)

@student_bp.route('/assignments/<int:assignment_id>')
@login_required
@student_required
def view_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if not enrollment:
        flash('You must be enrolled in the course to view this assignment.', 'danger')
        return redirect(url_for('student.browse_courses'))
    
    # Check if already submitted
    submission = Submission.query.filter_by(
        assignment_id=assignment.id,
        student_id=current_user.id
    ).first()
    
    form = SubmissionForm()
    
    return render_template('student/view_assignment.html', 
                           course=course, 
                           assignment=assignment, 
                           submission=submission, 
                           form=form)

def save_file(file):
    filename = secure_filename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    return os.path.join('uploads', filename)

@student_bp.route('/assignments/<int:assignment_id>/submit', methods=['POST'])
@login_required
@student_required
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    course = assignment.course
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if not enrollment:
        flash('You must be enrolled in the course to submit this assignment.', 'danger')
        return redirect(url_for('student.browse_courses'))
    
    # Check if already submitted
    existing_submission = Submission.query.filter_by(
        assignment_id=assignment.id,
        student_id=current_user.id
    ).first()
    
    if existing_submission:
        flash('You have already submitted this assignment.', 'info')
        return redirect(url_for('student.view_assignment', assignment_id=assignment.id))
    
    form = SubmissionForm()
    if form.validate_on_submit():
        file_path = None
        if form.file.data:
            file_path = save_file(form.file.data)
        
        submission = Submission(
            content=form.content.data,
            file_path=file_path,
            student_id=current_user.id,
            assignment_id=assignment.id
        )
        db.session.add(submission)
        db.session.commit()
        flash('Assignment submitted successfully!', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')
    
    return redirect(url_for('student.view_assignment', assignment_id=assignment.id))

@student_bp.route('/my-assignments')
@login_required
@student_required
def my_assignments():
    # Get all enrollments for this student
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    course_ids = [enrollment.course_id for enrollment in enrollments]
    
    # Get all assignments for these courses
    assignments = Assignment.query.filter(Assignment.course_id.in_(course_ids)).all()
    
    # Get submissions for these assignments
    assignment_data = []
    for assignment in assignments:
        submission = Submission.query.filter_by(
            assignment_id=assignment.id,
            student_id=current_user.id
        ).first()
        
        assignment_data.append({
            'assignment': assignment,
            'course': assignment.course,
            'submission': submission
        })
    
    return render_template('student/my_assignments.html', assignment_data=assignment_data)

@student_bp.route('/courses/<int:course_id>/modules')
@login_required
@student_required
def view_course_modules(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if not enrollment:
        flash('You must be enrolled in this course to view modules.', 'danger')
        return redirect(url_for('student.browse_courses'))
    
    # Check if the payment has been verified
    if not enrollment.payment_verified:
        flash('Your payment for this course is pending verification. You will have full access to course modules once your payment is verified.', 'warning')
        return redirect(url_for('student.view_course', course_id=course.id))
    
    # Get all modules for this course
    modules = Module.query.filter_by(course_id=course.id).order_by(Module.order).all()
    
    # Get progress for each module
    module_data = []
    for module in modules:
        progress = ModuleProgress.query.filter_by(
            student_id=current_user.id,
            module_id=module.id
        ).first()
        
        # Count completed tests
        test_count = Test.query.filter_by(module_id=module.id).count()
        passed_tests = 0
        
        tests = Test.query.filter_by(module_id=module.id).all()
        for test in tests:
            # Check if any attempt passed
            best_attempt = TestAttempt.query.filter_by(
                test_id=test.id,
                student_id=current_user.id,
                passed=True
            ).first()
            
            if best_attempt:
                passed_tests += 1
        
        # Calculate test completion percentage
        test_completion = 0
        if test_count > 0:
            test_completion = (passed_tests / test_count) * 100
        
        module_data.append({
            'module': module,
            'completed': progress.completed if progress else False,
            'test_count': test_count,
            'passed_tests': passed_tests,
            'test_completion': test_completion
        })
    
    return render_template('student/view_course_modules.html',
                          course=course,
                          module_data=module_data,
                          enrollment=enrollment)

@student_bp.route('/modules/<int:module_id>')
@login_required
@student_required
def view_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if not enrollment:
        flash('You must be enrolled in this course to view modules.', 'danger')
        return redirect(url_for('student.browse_courses'))
    
    # Get materials and tests for this module
    materials = Material.query.filter_by(module_id=module.id).order_by(Material.order).all()
    tests = Test.query.filter_by(module_id=module.id).all()
    
    # Get test progress
    test_data = []
    for test in tests:
        # Get best attempt (highest score)
        best_attempt = TestAttempt.query.filter_by(
            test_id=test.id,
            student_id=current_user.id
        ).order_by(TestAttempt.score.desc()).first()
        
        test_data.append({
            'test': test,
            'attempt': best_attempt,
            'passed': best_attempt.passed if best_attempt else False,
            'attempts_count': TestAttempt.query.filter_by(
                test_id=test.id,
                student_id=current_user.id
            ).count()
        })
    
    # Check if module is completed
    progress = ModuleProgress.query.filter_by(
        student_id=current_user.id,
        module_id=module.id
    ).first()
    
    if not progress:
        progress = ModuleProgress(
            student_id=current_user.id,
            module_id=module.id,
            completed=False
        )
        db.session.add(progress)
        db.session.commit()
    
    return render_template('student/view_module.html',
                          course=course,
                          module=module,
                          materials=materials,
                          test_data=test_data,
                          progress=progress)

@student_bp.route('/modules/<int:module_id>/complete')
@login_required
@student_required
def complete_module(module_id):
    module = Module.query.get_or_404(module_id)
    course = module.course
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if not enrollment:
        flash('You must be enrolled in this course to complete modules.', 'danger')
        return redirect(url_for('student.browse_courses'))
    
    # Get progress or create it if it doesn't exist
    progress = ModuleProgress.query.filter_by(
        student_id=current_user.id,
        module_id=module.id
    ).first()
    
    if not progress:
        progress = ModuleProgress(
            student_id=current_user.id,
            module_id=module.id
        )
        db.session.add(progress)
    
    # Check if all tests are passed
    tests = Test.query.filter_by(module_id=module.id).all()
    all_tests_passed = True
    
    for test in tests:
        passed_attempt = TestAttempt.query.filter_by(
            test_id=test.id,
            student_id=current_user.id,
            passed=True
        ).first()
        
        if not passed_attempt:
            all_tests_passed = False
            break
    
    if tests and not all_tests_passed:
        flash('You must pass all tests to complete this module.', 'warning')
        return redirect(url_for('student.view_module', module_id=module.id))
    
    # Mark as completed
    progress.completed = True
    progress.completed_at = datetime.utcnow()
    db.session.commit()
    
    flash('Module completed successfully!', 'success')
    return redirect(url_for('student.view_course_modules', course_id=course.id))

@student_bp.route('/tests/<int:test_id>')
@login_required
@student_required
def view_test(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if not enrollment:
        flash('You must be enrolled in this course to take tests.', 'danger')
        return redirect(url_for('student.browse_courses'))
    
    # Get previous attempts
    attempts = TestAttempt.query.filter_by(
        test_id=test.id,
        student_id=current_user.id
    ).order_by(TestAttempt.started_at.desc()).all()
    
    # Check if there's an ongoing attempt
    ongoing_attempt = TestAttempt.query.filter_by(
        test_id=test.id,
        student_id=current_user.id,
        completed_at=None
    ).first()
    
    return render_template('student/view_test.html',
                          course=course,
                          module=module,
                          test=test,
                          attempts=attempts,
                          ongoing_attempt=ongoing_attempt)

@student_bp.route('/tests/<int:test_id>/start')
@login_required
@student_required
def start_test(test_id):
    test = Test.query.get_or_404(test_id)
    module = test.module
    course = module.course
    
    # Check if student is enrolled
    enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course.id
    ).first()
    
    if not enrollment:
        flash('You must be enrolled in this course to take tests.', 'danger')
        return redirect(url_for('student.browse_courses'))
    
    # Check if there's an ongoing attempt
    ongoing_attempt = TestAttempt.query.filter_by(
        test_id=test.id,
        student_id=current_user.id,
        completed_at=None
    ).first()
    
    if ongoing_attempt:
        return redirect(url_for('student.take_test', attempt_id=ongoing_attempt.id))
    
    # Create a new attempt
    attempt = TestAttempt(
        student_id=current_user.id,
        test_id=test.id,
        started_at=datetime.utcnow()
    )
    db.session.add(attempt)
    db.session.commit()
    
    return redirect(url_for('student.take_test', attempt_id=attempt.id))

@student_bp.route('/test-attempts/<int:attempt_id>', methods=['GET', 'POST'])
@login_required
@student_required
def take_test(attempt_id):
    attempt = TestAttempt.query.get_or_404(attempt_id)
    test = attempt.test
    module = test.module
    course = module.course
    
    # Ensure the attempt belongs to the current user
    if attempt.student_id != current_user.id:
        flash('You do not have permission to access this test attempt.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Check if the attempt is already completed
    if attempt.completed_at:
        return redirect(url_for('student.view_test_results', attempt_id=attempt.id))
    
    # Get all questions for this test
    questions = Question.query.filter_by(test_id=test.id).all()
    
    # Process form submission
    form = TestAttemptForm()
    if form.validate_on_submit():
        total_points = 0
        earned_points = 0
        
        for question in questions:
            # Process each question's answer
            if question.question_type == 'multiple_choice':
                # Get selected option IDs from form
                option_key = f'question_{question.id}'
                selected_options = request.form.getlist(option_key)
                selected_options_str = ','.join(selected_options)
                
                # Calculate points for multiple choice
                correct_options = QuestionOption.query.filter_by(
                    question_id=question.id,
                    is_correct=True
                ).all()
                
                correct_option_ids = [str(opt.id) for opt in correct_options]
                
                # Only award points if the selection exactly matches the correct answers
                is_correct = set(selected_options) == set(correct_option_ids)
                points_earned = question.points if is_correct else 0
                
                answer = TestAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    selected_options=selected_options_str,
                    points_earned=points_earned
                )
                db.session.add(answer)
                
            elif question.question_type == 'true_false':
                # True/False is a special case of multiple choice
                option_key = f'question_{question.id}'
                selected_option = request.form.get(option_key)
                
                if selected_option:
                    # Find if the selected option is correct
                    option = QuestionOption.query.get(int(selected_option))
                    points_earned = question.points if option and option.is_correct else 0
                    
                    answer = TestAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        selected_options=selected_option,
                        points_earned=points_earned
                    )
                    db.session.add(answer)
                else:
                    # No answer provided
                    answer = TestAnswer(
                        attempt_id=attempt.id,
                        question_id=question.id,
                        points_earned=0
                    )
                    db.session.add(answer)
            
            elif question.question_type == 'essay':
                # For essay questions, just save the response (teacher will grade manually)
                answer_key = f'question_{question.id}_essay'
                answer_text = request.form.get(answer_key, '')
                
                answer = TestAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    answer_text=answer_text,
                    points_earned=0  # Essay questions need manual grading
                )
                db.session.add(answer)
            
            # Update point totals
            total_points += question.points
            earned_points += answer.points_earned if hasattr(answer, 'points_earned') else 0
        
        # Calculate score as a percentage
        score = (earned_points / total_points * 100) if total_points > 0 else 0
        
        # Update the attempt record
        attempt.score = score
        attempt.passed = score >= test.passing_score
        attempt.completed_at = datetime.utcnow()
        db.session.commit()
        
        flash('Test submitted successfully!', 'success')
        return redirect(url_for('student.view_test_results', attempt_id=attempt.id))
    
    # Prepare question data for the template
    question_data = []
    for question in questions:
        options = []
        if question.question_type in ['multiple_choice', 'true_false']:
            options = QuestionOption.query.filter_by(question_id=question.id).all()
        
        question_data.append({
            'question': question,
            'options': options
        })
    
    return render_template('student/take_test.html',
                          course=course,
                          module=module,
                          test=test,
                          attempt=attempt,
                          question_data=question_data,
                          form=form)

@student_bp.route('/test-attempts/<int:attempt_id>/results')
@login_required
@student_required
def view_test_results(attempt_id):
    attempt = TestAttempt.query.get_or_404(attempt_id)
    test = attempt.test
    module = test.module
    course = module.course
    
    # Ensure the attempt belongs to the current user
    if attempt.student_id != current_user.id:
        flash('You do not have permission to access these results.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Check if the attempt is completed
    if not attempt.completed_at:
        flash('This test has not been completed yet.', 'warning')
        return redirect(url_for('student.take_test', attempt_id=attempt.id))
    
    # Get all questions and answers
    questions = Question.query.filter_by(test_id=test.id).all()
    
    # Prepare results data
    result_data = []
    for question in questions:
        answer = TestAnswer.query.filter_by(
            attempt_id=attempt.id,
            question_id=question.id
        ).first()
        
        options = []
        selected_options = []
        
        if question.question_type in ['multiple_choice', 'true_false']:
            options = QuestionOption.query.filter_by(question_id=question.id).all()
            
            if answer and answer.selected_options:
                selected_ids = answer.selected_options.split(',')
                selected_options = [int(opt_id) for opt_id in selected_ids if opt_id]
        
        result_data.append({
            'question': question,
            'answer': answer,
            'options': options,
            'selected_options': selected_options
        })
    
    return render_template('student/test_results.html',
                          course=course,
                          module=module,
                          test=test,
                          attempt=attempt,
                          result_data=result_data)

@student_bp.route('/grades')
@login_required
@student_required
def view_grades():
    # Get all enrollments for this student
    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    
    # Prepare course data with grades
    course_data = []
    for enrollment in enrollments:
        course = enrollment.course
        
        # Get assignment grades
        assignment_grades = []
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        
        for assignment in assignments:
            submission = Submission.query.filter_by(
                assignment_id=assignment.id,
                student_id=current_user.id
            ).first()
            
            if submission and submission.grade is not None:
                assignment_grades.append({
                    'name': assignment.title,
                    'grade': submission.grade,
                    'feedback': submission.feedback,
                    'submitted_at': submission.submitted_at,
                    'graded_at': submission.graded_at
                })
        
        # Get test grades
        test_grades = []
        module_ids = [module.id for module in Module.query.filter_by(course_id=course.id).all()]
        
        if module_ids:
            tests = Test.query.filter(Test.module_id.in_(module_ids)).all()
            
            for test in tests:
                # Get the best attempt
                best_attempt = TestAttempt.query.filter_by(
                    test_id=test.id,
                    student_id=current_user.id
                ).order_by(TestAttempt.score.desc()).first()
                
                if best_attempt and best_attempt.score is not None:
                    test_grades.append({
                        'name': test.title,
                        'grade': best_attempt.score,
                        'passed': best_attempt.passed,
                        'completed_at': best_attempt.completed_at
                    })
        
        # Calculate course completion percentage
        modules = Module.query.filter_by(course_id=course.id).all()
        total_modules = len(modules)
        completed_modules = 0
        
        for module in modules:
            progress = ModuleProgress.query.filter_by(
                module_id=module.id,
                student_id=current_user.id,
                completed=True
            ).first()
            
            if progress:
                completed_modules += 1
        
        completion_percentage = (completed_modules / total_modules * 100) if total_modules > 0 else 0
        
        course_data.append({
            'course': course,
            'overall_grade': enrollment.overall_grade,
            'assignment_grades': assignment_grades,
            'test_grades': test_grades,
            'completion_percentage': completion_percentage
        })
    
    return render_template('student/view_grades.html', course_data=course_data)

@student_bp.route('/teacher-application', methods=['GET', 'POST'])
@login_required
@student_required
def teacher_application():
    # Check if already has a certificate or application pending
    if current_user.certificate_path:
        if current_user.certificate_verified:
            flash('Your certificate has already been verified. You can now teach courses.', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Your application is still under review. You will be notified when it is processed.', 'info')
            return redirect(url_for('auth.profile'))
    
    form = CertificateForm()
    if form.validate_on_submit():
        try:
            # Handle certificate upload
            certificate_file = form.certificate.data
            filename = secure_filename(certificate_file.filename)
            # Create a unique filename
            unique_filename = f"certificate_{current_user.id}_{int(datetime.utcnow().timestamp())}_{filename}"
            certificate_path = os.path.join('uploads', 'certificates', unique_filename)
            
            # Make sure the directory exists
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Save the file
            certificate_file.save(os.path.join(upload_dir, unique_filename))
            
            # Update user record
            current_user.certificate_path = certificate_path
            current_user.certificate_description = form.description.data
            current_user.certificate_submitted_at = datetime.utcnow()
            current_user.certificate_verified = False
            
            db.session.commit()
            flash('Your application has been submitted and is awaiting review.', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Certificate upload error: {str(e)}")
            flash(f'Error uploading certificate: {str(e)}', 'danger')
    
    return render_template('student/teacher_application.html', form=form)