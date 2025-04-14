from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, SubmitField, FloatField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from lms.models.user import User

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    is_admin = BooleanField('Register as Admin')
    admin_code = PasswordField('Admin Registration Code')
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different email.')

class TeacherCreationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Create Teacher Account')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different email.')

class ProfileUpdateForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Update Profile')
    
    def __init__(self, original_email, *args, **kwargs):
        super(ProfileUpdateForm, self).__init__(*args, **kwargs)
        self.original_email = original_email
    
    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email is already registered. Please use a different email.')

class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class CourseCreationForm(FlaskForm):
    title = StringField('Course Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Course Description', validators=[DataRequired()])
    category = SelectField('Category', coerce=int, validators=[DataRequired()])
    course_image = FileField('Course Image', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Images only!')])
    submit = SubmitField('Create Course')

def content_required_for_text_or_link(form, field):
    """Validate that content is provided for text or link types"""
    if form.content_type.data in ['text', 'link'] and not field.data:
        raise ValidationError('Content is required for text or link type materials')

class MaterialForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    content_type = SelectField('Type', choices=[
        ('text', 'Text Content'),
        ('file', 'File Upload'),
        ('link', 'External Link')
    ], validators=[DataRequired()])
    content = TextAreaField('Content', validators=[content_required_for_text_or_link])
    file = FileField('File', validators=[Optional(), FileAllowed(['pdf', 'doc', 'docx', 'ppt', 'pptx', 'jpg', 'png', 'zip'])])
    submit = SubmitField('Add Material')

class AssignmentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Add Assignment')

class SubmissionForm(FlaskForm):
    content = TextAreaField('Your Answer')
    file = FileField('Upload File', validators=[FileAllowed(['pdf', 'doc', 'docx', 'txt', 'jpg', 'png', 'zip'])])
    submit = SubmitField('Submit Assignment')

class GradingForm(FlaskForm):
    grade = FloatField('Grade', validators=[DataRequired()])
    feedback = TextAreaField('Feedback', validators=[DataRequired()])
    submit = SubmitField('Submit Grade')

class ModuleForm(FlaskForm):
    title = StringField('Module Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Module Description', validators=[DataRequired()])
    order = FloatField('Display Order', default=0)
    submit = SubmitField('Create Module')

class TestForm(FlaskForm):
    title = StringField('Test Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Test Description', validators=[DataRequired()])
    passing_score = FloatField('Passing Score (%)', default=70.0)
    submit = SubmitField('Create Test')

class QuestionForm(FlaskForm):
    question_text = TextAreaField('Question', validators=[DataRequired()])
    question_type = SelectField('Question Type', choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('essay', 'Essay Question')
    ], validators=[DataRequired()])
    points = FloatField('Points', default=1.0)
    submit = SubmitField('Add Question')

class OptionForm(FlaskForm):
    option_text = TextAreaField('Option', validators=[DataRequired()])
    is_correct = BooleanField('Correct Answer')
    submit = SubmitField('Add Option')

class TestAttemptForm(FlaskForm):
    submit = SubmitField('Submit Test')