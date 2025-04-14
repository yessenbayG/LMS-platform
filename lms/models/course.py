from datetime import datetime
import re
from lms.utils.db import db

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    courses = db.relationship('Course', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Course(db.Model):
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)  # New field for course activation status
    is_approved = db.Column(db.Boolean, default=False)  # Field for admin approval status
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    materials = db.relationship('Material', backref='course', lazy='dynamic', cascade="all, delete-orphan")
    assignments = db.relationship('Assignment', backref='course', lazy='dynamic', cascade="all, delete-orphan")
    enrollments = db.relationship('Enrollment', back_populates='course', lazy='dynamic', cascade="all, delete-orphan")
    modules = db.relationship('Module', backref='course', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Course {self.title}>'

class Material(db.Model):
    __tablename__ = 'materials'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # text, file, link, youtube
    content = db.Column(db.Text, nullable=True)  # Changed to nullable=True for file uploads
    file_path = db.Column(db.String(255))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=True)
    order = db.Column(db.Integer, default=0)  # For ordering materials within a module
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Material {self.title}>'
        
    @property
    def youtube_embed_url(self):
        """Extract YouTube video ID and return embed URL if this is a YouTube link"""
        if self.content_type != 'link':
            return None
            
        # YouTube URL patterns
        youtube_patterns = [
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, self.content)
            if match:
                video_id = match.group(1)
                return f'https://www.youtube.com/embed/{video_id}'
        
        return None
        
    @property
    def is_youtube(self):
        """Check if this material is a YouTube video"""
        return self.content_type == 'link' and self.youtube_embed_url is not None

class Assignment(db.Model):
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    submissions = db.relationship('Submission', backref='assignment', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Assignment {self.title}>'

class Submission(db.Model):
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    graded_at = db.Column(db.DateTime)
    
    # Relationships
    student = db.relationship('User', back_populates='submissions')
    
    def __repr__(self):
        return f'<Submission {self.id}>'

class Module(db.Model):
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)  # For ordering modules in a course
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    materials = db.relationship('Material', backref='module', lazy='dynamic', cascade="all, delete-orphan")
    tests = db.relationship('Test', backref='module', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Module {self.title}>'

class Test(db.Model):
    __tablename__ = 'tests'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    passing_score = db.Column(db.Float, default=70.0)  # Default passing score is 70%
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='test', lazy='dynamic', cascade="all, delete-orphan")
    attempts = db.relationship('TestAttempt', backref='test', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Test {self.title}>'

class Question(db.Model):
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # multiple_choice, true_false, essay
    points = db.Column(db.Float, default=1.0)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False)
    
    # Relationships
    options = db.relationship('QuestionOption', backref='question', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Question {self.id}>'

class QuestionOption(db.Model):
    __tablename__ = 'question_options'
    
    id = db.Column(db.Integer, primary_key=True)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    
    def __repr__(self):
        return f'<QuestionOption {self.id}>'

class TestAttempt(db.Model):
    __tablename__ = 'test_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False)
    score = db.Column(db.Float)
    passed = db.Column(db.Boolean)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    answers = db.relationship('TestAnswer', backref='attempt', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<TestAttempt {self.id}>'

class TestAnswer(db.Model):
    __tablename__ = 'test_answers'
    
    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('test_attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    answer_text = db.Column(db.Text)  # For essay questions
    selected_options = db.Column(db.String(255))  # Comma-separated IDs for multiple choice
    points_earned = db.Column(db.Float, default=0)
    
    # Relationship for the question
    question = db.relationship('Question')
    
    def __repr__(self):
        return f'<TestAnswer {self.id}>'

class ModuleProgress(db.Model):
    __tablename__ = 'module_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    student = db.relationship('User', backref='module_progress')
    module = db.relationship('Module')
    
    __table_args__ = (db.UniqueConstraint('student_id', 'module_id'),)
    
    def __repr__(self):
        return f'<ModuleProgress {self.id}>'

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    overall_grade = db.Column(db.Float)
    
    # Relationships
    student = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')
    
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id'),)
    
    def __repr__(self):
        return f'<Enrollment {self.id}>'