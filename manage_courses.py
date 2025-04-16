#!/usr/bin/env python3

import os
import sys
import argparse
from datetime import datetime
from flask import Flask
import random

# Setup Flask app context to use models
app = Flask(
    __name__,
    template_folder='lms/templates',
    static_folder='lms/static'
)
app.config['SECRET_KEY'] = 'dev-secret-key'
# Get the absolute path to the database file
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'lms.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms/static/uploads')

# Import db after app config
from lms.utils.db import db
db.init_app(app)

# Now import models
from lms.models.user import User, Role
from lms.models.course import (
    Course, Category, Material, Module, Test, 
    Question, QuestionOption, Assignment, Enrollment
)

MOCK_COURSE_TITLES = ["Introduction to Programming", "Web Development Fundamentals"]

#======================================================================
# DELETION FUNCTIONS
#======================================================================

def delete_course(course_id=None, course_title=None, commit=True):
    """Delete a course and all its associated content"""
    with app.app_context():
        if course_id:
            course = Course.query.get(course_id)
        elif course_title:
            course = Course.query.filter_by(title=course_title).first()
        else:
            print("Error: Either course_id or course_title must be provided.")
            return False
        
        if not course:
            print(f"No course found with {'ID ' + str(course_id) if course_id else 'title ' + course_title}")
            return False
        
        print(f"Deleting course: {course.title} (ID: {course.id})")
        
        # Delete enrollments
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        for enrollment in enrollments:
            db.session.delete(enrollment)
        print(f"  - Deleted {len(enrollments)} enrollments")
        
        # Delete assignments
        assignments = Assignment.query.filter_by(course_id=course.id).all()
        for assignment in assignments:
            # Delete submissions for each assignment
            from lms.models.course import Submission
            submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
            for submission in submissions:
                db.session.delete(submission)
            db.session.delete(assignment)
        print(f"  - Deleted {len(assignments)} assignments")
        
        # Delete modules and associated content
        modules = Module.query.filter_by(course_id=course.id).all()
        module_count = len(modules)
        
        for module in modules:
            delete_module(module.id, commit=False)
        
        # Delete any course materials that aren't associated with modules
        materials = Material.query.filter_by(course_id=course.id, module_id=None).all()
        for material in materials:
            db.session.delete(material)
        print(f"  - Deleted {len(materials)} course-level materials")
        
        # Finally, delete the course
        db.session.delete(course)
        
        if commit:
            db.session.commit()
            print(f"Course '{course.title}' and all associated content deleted successfully!")
        
        return True

def delete_module(module_id, commit=True):
    """Delete a module and all its associated content"""
    with app.app_context():
        module = Module.query.get(module_id)
        if not module:
            print(f"No module found with ID {module_id}")
            return False
        
        print(f"  - Deleting module: {module.title} (ID: {module.id})")
        
        # Delete materials in this module
        materials = Material.query.filter_by(module_id=module.id).all()
        for material in materials:
            db.session.delete(material)
        print(f"    - Deleted {len(materials)} materials")
        
        # Delete tests and associated content
        tests = Test.query.filter_by(module_id=module.id).all()
        for test in tests:
            delete_test(test.id, commit=False)
        
        # Delete module progress records
        from lms.models.course import ModuleProgress
        progress_records = ModuleProgress.query.filter_by(module_id=module.id).all()
        for record in progress_records:
            db.session.delete(record)
        print(f"    - Deleted {len(progress_records)} progress records")
        
        # Delete the module itself
        db.session.delete(module)
        
        if commit:
            db.session.commit()
            print(f"Module '{module.title}' deleted successfully!")
        
        return True

def delete_test(test_id, commit=True):
    """Delete a test and all its associated content"""
    with app.app_context():
        test = Test.query.get(test_id)
        if not test:
            print(f"No test found with ID {test_id}")
            return False
        
        print(f"    - Deleting test: {test.title} (ID: {test.id})")
        
        # Delete test attempts and answers
        from lms.models.course import TestAttempt, TestAnswer
        attempts = TestAttempt.query.filter_by(test_id=test.id).all()
        for attempt in attempts:
            # Delete answers for this attempt
            answers = TestAnswer.query.filter_by(attempt_id=attempt.id).all()
            for answer in answers:
                db.session.delete(answer)
            db.session.delete(attempt)
        print(f"      - Deleted {len(attempts)} test attempts")
        
        # Delete questions and options
        questions = Question.query.filter_by(test_id=test.id).all()
        question_count = 0
        option_count = 0
        
        for question in questions:
            # Delete options for this question
            options = QuestionOption.query.filter_by(question_id=question.id).all()
            for option in options:
                db.session.delete(option)
            option_count += len(options)
            
            db.session.delete(question)
            question_count += 1
        
        print(f"      - Deleted {question_count} questions with {option_count} options")
        
        # Delete the test itself
        db.session.delete(test)
        
        if commit:
            db.session.commit()
            print(f"Test '{test.title}' deleted successfully!")
        
        return True

def deactivate_course(course_id=None, course_title=None):
    """
    Deactivate a course without deleting it
    This can be implemented by adding an is_active field to the Course model
    Since we don't have that field yet, we'll show a message
    """
    with app.app_context():
        if course_id:
            course = Course.query.get(course_id)
        elif course_title:
            course = Course.query.filter_by(title=course_title).first()
        else:
            print("Error: Either course_id or course_title must be provided.")
            return False
        
        if not course:
            print(f"No course found with {'ID ' + str(course_id) if course_id else 'title ' + course_title}")
            return False
        
        # If we don't have is_active field, show a message
        print(f"Note: The Course model doesn't have an is_active field.")
        print(f"You need to add this field to implement course deactivation.")
        print(f"For now, you can delete the course instead.")
        
        return False

def delete_all_mock_courses():
    """Delete all mock courses created by this script"""
    with app.app_context():
        print("\nDeleting all mock courses...")
        
        for title in MOCK_COURSE_TITLES:
            course = Course.query.filter_by(title=title).first()
            if course:
                delete_course(course_id=course.id)
            else:
                print(f"Course '{title}' not found.")
        
        print("Done deleting mock courses.")

#======================================================================
# CREATION FUNCTIONS
#======================================================================

def create_programming_course(teacher):
    """Create Introduction to Programming course"""
    with app.app_context():
        print("\nCreating 'Introduction to Programming' course...")
        
        cs_category = Category.query.filter_by(name='Computer Science').first()
        if not cs_category:
            print("Computer Science category not found. Creating it...")
            cs_category = Category(name='Computer Science', description='Computer programming and software development')
            db.session.add(cs_category)
            db.session.commit()
        
        programming_course = Course(
            title="Introduction to Programming",
            description=(
                "This course provides a comprehensive introduction to programming concepts "
                "using Python. Students will learn the fundamentals of programming, including "
                "variables, control flow, functions, and basic data structures. Perfect for "
                "beginners with no prior programming experience."
            ),
            category_id=cs_category.id,
            teacher_id=teacher.id,
            image_path="uploads/course_images/programming.jpg"
        )
        db.session.add(programming_course)
        db.session.flush()  # Get the course ID
        
        # Module 1: Getting Started with Python
        module1 = Module(
            title="Getting Started with Python",
            description="Learn the basics of Python programming and set up your development environment.",
            order=1,
            course_id=programming_course.id
        )
        db.session.add(module1)
        db.session.flush()
        
        # Add materials to Module 1
        materials = [
            Material(
                title="Introduction to Programming",
                content_type="text",
                content=(
                    "# Introduction to Programming\n\n"
                    "Programming is the process of creating a set of instructions that tell a computer how to perform a task. "
                    "Programming can be done using a variety of computer programming languages, such as JavaScript, Python, and C++.\n\n"
                    "## Why Learn Programming?\n\n"
                    "1. **Problem Solving Skills**: Programming teaches you to break down complex problems into smaller, manageable parts.\n"
                    "2. **Career Opportunities**: Programming skills are in high demand across many industries.\n"
                    "3. **Automation**: You can automate repetitive tasks to save time.\n"
                    "4. **Understanding Technology**: Programming helps you understand how the digital world works."
                ),
                module_id=module1.id,
                course_id=programming_course.id,
                order=1
            ),
            Material(
                title="Setting Up Python",
                content_type="text",
                content=(
                    "# Setting Up Python\n\n"
                    "Before we start coding, we need to set up Python on your computer. Follow these steps:\n\n"
                    "1. Visit the official Python website at [python.org](https://python.org)\n"
                    "2. Download the latest version of Python (Python 3.x)\n"
                    "3. Run the installer and make sure to check 'Add Python to PATH'\n"
                    "4. Open a terminal or command prompt and type `python --version` to verify installation\n\n"
                    "## Recommended Code Editors\n\n"
                    "- **Visual Studio Code**: Free, lightweight, and extensible\n"
                    "- **PyCharm**: Powerful IDE specifically designed for Python\n"
                    "- **Jupyter Notebooks**: Great for data science and learning"
                ),
                module_id=module1.id,
                course_id=programming_course.id,
                order=2
            ),
            Material(
                title="Your First Python Program",
                content_type="link",
                content="https://youtu.be/kqtD5dpn9C8",
                module_id=module1.id,
                course_id=programming_course.id,
                order=3
            )
        ]
        
        for material in materials:
            db.session.add(material)
        
        # Create a test for Module 1
        test1 = Test(
            title="Python Basics Quiz",
            description="Test your understanding of basic Python concepts.",
            passing_score=70.0,
            module_id=module1.id
        )
        db.session.add(test1)
        db.session.flush()
        
        # Add questions to the test
        questions = [
            {
                "text": "What is the correct file extension for Python files?",
                "type": "multiple_choice",
                "options": [
                    {".py": True},
                    {".python": False},
                    {".p": False},
                    {".pyth": False}
                ]
            },
            {
                "text": "How do you create a comment in Python?",
                "type": "multiple_choice",
                "options": [
                    {"# This is a comment": True},
                    {"// This is a comment": False},
                    {"/* This is a comment */": False},
                    {"<!-- This is a comment -->": False}
                ]
            },
            {
                "text": "Python is an interpreted language.",
                "type": "true_false",
                "correct": True
            }
        ]
        
        for q_data in questions:
            if q_data["type"] == "true_false":
                question = Question(
                    question_text=q_data["text"],
                    question_type="true_false",
                    points=1.0,
                    test_id=test1.id
                )
                db.session.add(question)
                db.session.flush()
                
                # Add True/False options
                true_option = QuestionOption(
                    option_text="True",
                    is_correct=q_data["correct"],
                    question_id=question.id
                )
                false_option = QuestionOption(
                    option_text="False",
                    is_correct=not q_data["correct"],
                    question_id=question.id
                )
                db.session.add_all([true_option, false_option])
            else:  # multiple_choice
                question = Question(
                    question_text=q_data["text"],
                    question_type=q_data["type"],
                    points=1.0,
                    test_id=test1.id
                )
                db.session.add(question)
                db.session.flush()
                
                # Add options
                for option_dict in q_data["options"]:
                    for text, is_correct in option_dict.items():
                        option = QuestionOption(
                            option_text=text,
                            is_correct=is_correct,
                            question_id=question.id
                        )
                        db.session.add(option)
        
        # Module 2: Variables and Data Types
        module2 = Module(
            title="Variables and Data Types",
            description="Learn about variables, data types, and basic operations in Python.",
            order=2,
            course_id=programming_course.id
        )
        db.session.add(module2)
        db.session.flush()
        
        # Add materials to Module 2
        materials = [
            Material(
                title="Python Variables",
                content_type="text",
                content=(
                    "# Python Variables\n\n"
                    "Variables are containers for storing data values. In Python, you don't need to declare a variable's type—Python does this automatically based on the assigned value.\n\n"
                    "## Creating Variables\n\n"
                    "```python\n"
                    "# Assigning values to variables\n"
                    "x = 5           # x is an integer\n"
                    "name = \"John\"   # name is a string\n"
                    "is_student = True  # is_student is a boolean\n"
                    "```\n\n"
                    "## Variable Naming Rules\n\n"
                    "1. Variable names must start with a letter or underscore\n"
                    "2. Variable names cannot start with a number\n"
                    "3. Variable names can only contain alpha-numeric characters and underscores (A-z, 0-9, and _)\n"
                    "4. Variable names are case-sensitive (age, Age, and AGE are different variables)\n\n"
                    "## Good Practice\n\n"
                    "- Use descriptive names (e.g., `student_count` instead of `sc`)\n"
                    "- Use snake_case for variable names (words separated by underscores)\n"
                    "- Avoid using Python reserved words like `if`, `else`, `for`, etc."
                ),
                module_id=module2.id,
                course_id=programming_course.id,
                order=1
            ),
            Material(
                title="Python Data Types",
                content_type="text",
                content=(
                    "# Python Data Types\n\n"
                    "Python has several built-in data types that you'll use regularly:\n\n"
                    "## Numeric Types\n\n"
                    "- **int**: Integer values like `5`, `-10`, `1000`\n"
                    "- **float**: Decimal values like `5.25`, `-0.5`, `3.14`\n"
                    "- **complex**: Complex numbers like `1+2j`\n\n"
                    "## Text Type\n\n"
                    "- **str**: Strings like `\"Hello\"`, `'Python'`, `\"123\"`\n\n"
                    "## Boolean Type\n\n"
                    "- **bool**: Either `True` or `False`\n\n"
                    "## Sequence Types\n\n"
                    "- **list**: Ordered, mutable collection like `[1, 2, 3]`\n"
                    "- **tuple**: Ordered, immutable collection like `(1, 2, 3)`\n"
                    "- **range**: Sequence of numbers like `range(6)` (0 to 5)\n\n"
                    "## Mapping Type\n\n"
                    "- **dict**: Key-value pairs like `{\"name\": \"John\", \"age\": 30}`\n\n"
                    "## Set Types\n\n"
                    "- **set**: Unordered collection of unique items like `{1, 2, 3}`\n"
                    "- **frozenset**: Immutable version of a set\n\n"
                    "## None Type\n\n"
                    "- **NoneType**: The value `None` represents the absence of a value"
                ),
                module_id=module2.id,
                course_id=programming_course.id,
                order=2
            ),
            Material(
                title="Python Variables Tutorial",
                content_type="link",
                content="https://youtu.be/cQT33yu9pY8",
                module_id=module2.id,
                course_id=programming_course.id,
                order=3
            )
        ]
        
        for material in materials:
            db.session.add(material)
        
        # Create a test for Module 2
        test2 = Test(
            title="Variables and Data Types Quiz",
            description="Test your understanding of Python variables and data types.",
            passing_score=70.0,
            module_id=module2.id
        )
        db.session.add(test2)
        db.session.flush()
        
        # Add questions to the test
        questions = [
            {
                "text": "Which of the following is a valid variable name in Python?",
                "type": "multiple_choice",
                "options": [
                    {"user_name": True},
                    {"2user": False},
                    {"user-name": False},
                    {"class": False}
                ]
            },
            {
                "text": "What is the data type of the value in x? x = 5.0",
                "type": "multiple_choice",
                "options": [
                    {"float": True},
                    {"int": False},
                    {"str": False},
                    {"double": False}
                ]
            },
            {
                "text": "In Python, variables must be declared with their type before use.",
                "type": "true_false",
                "correct": False
            }
        ]
        
        for q_data in questions:
            if q_data["type"] == "true_false":
                question = Question(
                    question_text=q_data["text"],
                    question_type="true_false",
                    points=1.0,
                    test_id=test2.id
                )
                db.session.add(question)
                db.session.flush()
                
                # Add True/False options
                true_option = QuestionOption(
                    option_text="True",
                    is_correct=q_data["correct"],
                    question_id=question.id
                )
                false_option = QuestionOption(
                    option_text="False",
                    is_correct=not q_data["correct"],
                    question_id=question.id
                )
                db.session.add_all([true_option, false_option])
            else:  # multiple_choice
                question = Question(
                    question_text=q_data["text"],
                    question_type=q_data["type"],
                    points=1.0,
                    test_id=test2.id
                )
                db.session.add(question)
                db.session.flush()
                
                # Add options
                for option_dict in q_data["options"]:
                    for text, is_correct in option_dict.items():
                        option = QuestionOption(
                            option_text=text,
                            is_correct=is_correct,
                            question_id=question.id
                        )
                        db.session.add(option)
        
        db.session.commit()
        return programming_course

def create_webdev_course(teacher):
    """Create Web Development Fundamentals course"""
    with app.app_context():
        print("\nCreating 'Web Development Fundamentals' course...")
        
        cs_category = Category.query.filter_by(name='Computer Science').first()
        if not cs_category:
            print("Computer Science category not found. Creating it...")
            cs_category = Category(name='Computer Science', description='Computer programming and software development')
            db.session.add(cs_category)
            db.session.commit()
        
        web_course = Course(
            title="Web Development Fundamentals",
            description=(
                "This course teaches the essential skills needed to build modern websites. "
                "You'll learn HTML for structure, CSS for styling, and JavaScript for interactivity. "
                "By the end of this course, you'll be able to create responsive, interactive web pages "
                "and understand the core technologies that power the web."
            ),
            category_id=cs_category.id,
            teacher_id=teacher.id,
            image_path="uploads/course_images/webdev.jpg"
        )
        db.session.add(web_course)
        db.session.flush()
        
        # Module 1: HTML Basics
        module1 = Module(
            title="HTML Basics",
            description="Learn the fundamentals of HTML, the standard markup language for creating web pages.",
            order=1,
            course_id=web_course.id
        )
        db.session.add(module1)
        db.session.flush()
        
        # Add materials to Module 1
        materials = [
            Material(
                title="Introduction to HTML",
                content_type="text",
                content=(
                    "# Introduction to HTML\n\n"
                    "HTML (HyperText Markup Language) is the standard markup language for creating web pages. It describes the structure of a web page and consists of a series of elements that tell the browser how to display the content.\n\n"
                    "## HTML Elements\n\n"
                    "HTML elements are represented by tags, written using angle brackets. For example:\n\n"
                    "```html\n"
                    "<h1>This is a Heading</h1>\n"
                    "<p>This is a paragraph.</p>\n"
                    "```\n\n"
                    "## HTML Document Structure\n\n"
                    "A basic HTML document looks like this:\n\n"
                    "```html\n"
                    "<!DOCTYPE html>\n"
                    "<html>\n"
                    "<head>\n"
                    "    <title>Page Title</title>\n"
                    "</head>\n"
                    "<body>\n"
                    "    <h1>My First Heading</h1>\n"
                    "    <p>My first paragraph.</p>\n"
                    "</body>\n"
                    "</html>\n"
                    "```\n\n"
                    "- The `<!DOCTYPE html>` declaration defines this document as HTML5\n"
                    "- The `<html>` element is the root element of an HTML page\n"
                    "- The `<head>` element contains meta information about the document\n"
                    "- The `<title>` element specifies a title for the document\n"
                    "- The `<body>` element contains the visible page content"
                ),
                module_id=module1.id,
                course_id=web_course.id,
                order=1
            ),
            Material(
                title="HTML Elements and Attributes",
                content_type="text",
                content=(
                    "# HTML Elements and Attributes\n\n"
                    "## Common HTML Elements\n\n"
                    "- **Headings**: `<h1>` to `<h6>`, with `<h1>` being the most important\n"
                    "- **Paragraphs**: `<p>`\n"
                    "- **Links**: `<a href=\"url\">link text</a>`\n"
                    "- **Images**: `<img src=\"image.jpg\" alt=\"description\">`\n"
                    "- **Lists**: \n"
                    "  - Unordered lists: `<ul>` with `<li>` items\n"
                    "  - Ordered lists: `<ol>` with `<li>` items\n"
                    "- **Divs**: `<div>` containers for grouping elements\n"
                    "- **Spans**: `<span>` for inline styling\n\n"
                    "## HTML Attributes\n\n"
                    "Attributes provide additional information about HTML elements:\n\n"
                    "- The `href` attribute specifies the URL of a link\n"
                    "- The `src` attribute specifies the path to an image\n"
                    "- The `alt` attribute provides alternative text for an image\n"
                    "- The `style` attribute adds styles to an element\n"
                    "- The `class` attribute specifies a class name for CSS styling\n"
                    "- The `id` attribute specifies a unique ID for an element\n\n"
                    "Example with attributes:\n\n"
                    "```html\n"
                    "<a href=\"https://www.example.com\" target=\"_blank\" title=\"Visit Example\">\n"
                    "  Visit Example Website\n"
                    "</a>\n"
                    "```"
                ),
                module_id=module1.id,
                course_id=web_course.id,
                order=2
            ),
            Material(
                title="HTML Tutorial for Beginners",
                content_type="link",
                content="https://youtu.be/qz0aGYrrlhU",
                module_id=module1.id,
                course_id=web_course.id,
                order=3
            )
        ]
        
        for material in materials:
            db.session.add(material)
        
        # Create a test for Module 1
        test1 = Test(
            title="HTML Basics Quiz",
            description="Test your understanding of basic HTML concepts.",
            passing_score=70.0,
            module_id=module1.id
        )
        db.session.add(test1)
        db.session.flush()
        
        # Add questions to the test
        questions = [
            {
                "text": "What does HTML stand for?",
                "type": "multiple_choice",
                "options": [
                    {"HyperText Markup Language": True},
                    {"Hyperlinks and Text Markup Language": False},
                    {"Home Tool Markup Language": False},
                    {"Hyper Technical Modern Language": False}
                ]
            },
            {
                "text": "Which HTML element is used for creating a hyperlink?",
                "type": "multiple_choice",
                "options": [
                    {"<a>": True},
                    {"<link>": False},
                    {"<href>": False},
                    {"<hyperlink>": False}
                ]
            },
            {
                "text": "HTML tags are case-sensitive.",
                "type": "true_false",
                "correct": False
            }
        ]
        
        for q_data in questions:
            if q_data["type"] == "true_false":
                question = Question(
                    question_text=q_data["text"],
                    question_type="true_false",
                    points=1.0,
                    test_id=test1.id
                )
                db.session.add(question)
                db.session.flush()
                
                # Add True/False options
                true_option = QuestionOption(
                    option_text="True",
                    is_correct=q_data["correct"],
                    question_id=question.id
                )
                false_option = QuestionOption(
                    option_text="False",
                    is_correct=not q_data["correct"],
                    question_id=question.id
                )
                db.session.add_all([true_option, false_option])
            else:  # multiple_choice
                question = Question(
                    question_text=q_data["text"],
                    question_type=q_data["type"],
                    points=1.0,
                    test_id=test1.id
                )
                db.session.add(question)
                db.session.flush()
                
                # Add options
                for option_dict in q_data["options"]:
                    for text, is_correct in option_dict.items():
                        option = QuestionOption(
                            option_text=text,
                            is_correct=is_correct,
                            question_id=question.id
                        )
                        db.session.add(option)
        
        # Module 2: CSS Basics
        module2 = Module(
            title="CSS Basics",
            description="Learn how to style HTML elements using CSS to create beautiful and responsive web pages.",
            order=2,
            course_id=web_course.id
        )
        db.session.add(module2)
        db.session.flush()
        
        # Add materials to Module 2
        materials = [
            Material(
                title="Introduction to CSS",
                content_type="text",
                content=(
                    "# Introduction to CSS\n\n"
                    "CSS (Cascading Style Sheets) is used to style and layout web pages. It controls how HTML elements look in the browser.\n\n"
                    "## Ways to Add CSS\n\n"
                    "1. **Inline CSS**: Using the `style` attribute in HTML elements\n"
                    "   ```html\n"
                    "   <h1 style=\"color: blue; text-align: center;\">Heading</h1>\n"
                    "   ```\n\n"
                    "2. **Internal CSS**: Using the `<style>` element in the `<head>` section\n"
                    "   ```html\n"
                    "   <head>\n"
                    "       <style>\n"
                    "           body { background-color: lightblue; }\n"
                    "           h1 { color: navy; margin-left: 20px; }\n"
                    "       </style>\n"
                    "   </head>\n"
                    "   ```\n\n"
                    "3. **External CSS**: Using a separate CSS file\n"
                    "   ```html\n"
                    "   <head>\n"
                    "       <link rel=\"stylesheet\" href=\"styles.css\">\n"
                    "   </head>\n"
                    "   ```\n\n"
                    "## CSS Syntax\n\n"
                    "```css\n"
                    "selector {\n"
                    "    property: value;\n"
                    "    another-property: another-value;\n"
                    "}\n"
                    "```\n\n"
                    "For example:\n"
                    "```css\n"
                    "h1 {\n"
                    "    color: blue;\n"
                    "    font-size: 24px;\n"
                    "}\n"
                    "```"
                ),
                module_id=module2.id,
                course_id=web_course.id,
                order=1
            ),
            Material(
                title="CSS Selectors",
                content_type="text",
                content=(
                    "# CSS Selectors\n\n"
                    "CSS selectors define which HTML elements you want to style. There are several types of selectors:\n\n"
                    "## Simple Selectors\n\n"
                    "- **Element selector**: Selects elements based on tag name\n"
                    "  ```css\n"
                    "  p { color: red; }\n"
                    "  ```\n\n"
                    "- **Class selector**: Selects elements with a specific class attribute\n"
                    "  ```css\n"
                    "  .highlight { background-color: yellow; }\n"
                    "  ```\n\n"
                    "- **ID selector**: Selects an element with a specific id attribute\n"
                    "  ```css\n"
                    "  #header { font-size: 30px; }\n"
                    "  ```\n\n"
                    "## Combinator Selectors\n\n"
                    "- **Descendant selector**: Selects all elements that are descendants of a specified element\n"
                    "  ```css\n"
                    "  div p { background-color: lightgray; }\n"
                    "  ```\n\n"
                    "- **Child selector**: Selects all elements that are the direct children of a specified element\n"
                    "  ```css\n"
                    "  div > p { color: blue; }\n"
                    "  ```\n\n"
                    "- **Adjacent sibling selector**: Selects an element that directly follows another specific element\n"
                    "  ```css\n"
                    "  h1 + p { margin-top: 0; }\n"
                    "  ```\n\n"
                    "## Pseudo-class Selectors\n\n"
                    "- **:hover**: Applies when a user hovers over an element\n"
                    "  ```css\n"
                    "  a:hover { color: red; }\n"
                    "  ```\n\n"
                    "- **:focus**: Applies when an element has focus\n"
                    "  ```css\n"
                    "  input:focus { border-color: blue; }\n"
                    "  ```\n\n"
                    "- **:first-child**: Selects the first child of its parent\n"
                    "  ```css\n"
                    "  li:first-child { font-weight: bold; }\n"
                    "  ```"
                ),
                module_id=module2.id,
                course_id=web_course.id,
                order=2
            ),
            Material(
                title="CSS Tutorial - Zero to Hero",
                content_type="link",
                content="https://youtu.be/1Rs2ND1ryYc",
                module_id=module2.id,
                course_id=web_course.id,
                order=3
            )
        ]
        
        for material in materials:
            db.session.add(material)
        
        # Create a test for Module 2
        test2 = Test(
            title="CSS Basics Quiz",
            description="Test your understanding of basic CSS concepts.",
            passing_score=70.0,
            module_id=module2.id
        )
        db.session.add(test2)
        db.session.flush()
        
        # Add questions to the test
        questions = [
            {
                "text": "Which CSS property is used to change the text color of an element?",
                "type": "multiple_choice",
                "options": [
                    {"color": True},
                    {"text-color": False},
                    {"font-color": False},
                    {"text-style": False}
                ]
            },
            {
                "text": "How do you select an element with the id 'header' in CSS?",
                "type": "multiple_choice",
                "options": [
                    {"#header": True},
                    {".header": False},
                    {"header": False},
                    {"*header": False}
                ]
            },
            {
                "text": "In CSS, the property 'margin: 10px 20px;' sets the top and bottom margins to 10px, and the left and right margins to 20px.",
                "type": "true_false",
                "correct": True
            }
        ]
        
        for q_data in questions:
            if q_data["type"] == "true_false":
                question = Question(
                    question_text=q_data["text"],
                    question_type="true_false",
                    points=1.0,
                    test_id=test2.id
                )
                db.session.add(question)
                db.session.flush()
                
                # Add True/False options
                true_option = QuestionOption(
                    option_text="True",
                    is_correct=q_data["correct"],
                    question_id=question.id
                )
                false_option = QuestionOption(
                    option_text="False",
                    is_correct=not q_data["correct"],
                    question_id=question.id
                )
                db.session.add_all([true_option, false_option])
            else:  # multiple_choice
                question = Question(
                    question_text=q_data["text"],
                    question_type=q_data["type"],
                    points=1.0,
                    test_id=test2.id
                )
                db.session.add(question)
                db.session.flush()
                
                # Add options
                for option_dict in q_data["options"]:
                    for text, is_correct in option_dict.items():
                        option = QuestionOption(
                            option_text=text,
                            is_correct=is_correct,
                            question_id=question.id
                        )
                        db.session.add(option)
        
        db.session.commit()
        return web_course

def create_mock_courses():
    """Create all mock courses"""
    with app.app_context():
        print("\nCreating mock courses...")
        
        # Get teacher
        teacher = User.query.filter_by(email='teacher@gmail.com').first()
        if not teacher:
            print("Teacher account not found. Please create a teacher account first.")
            return
        
        # Delete existing mock courses if they exist
        for title in MOCK_COURSE_TITLES:
            existing_course = Course.query.filter_by(title=title).first()
            if existing_course:
                delete_course(course_id=existing_course.id)
        
        # Create programming course
        programming_course = create_programming_course(teacher)
        
        # Create web development course
        web_course = create_webdev_course(teacher)
        
        print("Mock courses created successfully!")
        return [programming_course, web_course]

def list_courses():
    """List all courses in the database"""
    with app.app_context():
        courses = Course.query.all()
        
        print("\nAll Courses:")
        print("-" * 80)
        print(f"{'ID':<4} {'Title':<40} {'Teacher':<20} {'Category':<15} {'Modules':<8}")
        print("-" * 80)
        
        for course in courses:
            teacher = User.query.get(course.teacher_id)
            teacher_name = f"{teacher.first_name} {teacher.last_name}" if teacher else "Unknown"
            
            category = Category.query.get(course.category_id)
            category_name = category.name if category else "Uncategorized"
            
            module_count = Module.query.filter_by(course_id=course.id).count()
            
            print(f"{course.id:<4} {course.title[:38]:<40} {teacher_name[:18]:<20} {category_name[:13]:<15} {module_count:<8}")
        
        print("-" * 80)

def list_modules(course_id):
    """List all modules for a specific course"""
    with app.app_context():
        course = Course.query.get(course_id)
        if not course:
            print(f"No course found with ID {course_id}")
            return
        
        modules = Module.query.filter_by(course_id=course.id).order_by(Module.order).all()
        
        print(f"\nModules for Course: {course.title} (ID: {course.id})")
        print("-" * 80)
        print(f"{'ID':<4} {'Title':<40} {'Materials':<10} {'Tests':<5} {'Order':<5}")
        print("-" * 80)
        
        for module in modules:
            material_count = Material.query.filter_by(module_id=module.id).count()
            test_count = Test.query.filter_by(module_id=module.id).count()
            
            print(f"{module.id:<4} {module.title[:38]:<40} {material_count:<10} {test_count:<5} {module.order:<5}")
        
        print("-" * 80)

def list_tests(module_id):
    """List all tests for a specific module"""
    with app.app_context():
        module = Module.query.get(module_id)
        if not module:
            print(f"No module found with ID {module_id}")
            return
        
        tests = Test.query.filter_by(module_id=module.id).all()
        
        print(f"\nTests for Module: {module.title} (ID: {module.id})")
        print("-" * 70)
        print(f"{'ID':<4} {'Title':<40} {'Passing Score':<15} {'Questions':<10}")
        print("-" * 70)
        
        for test in tests:
            question_count = Question.query.filter_by(test_id=test.id).count()
            
            print(f"{test.id:<4} {test.title[:38]:<40} {test.passing_score:<15} {question_count:<10}")
        
        print("-" * 70)

def list_materials(module_id):
    """List all materials for a specific module"""
    with app.app_context():
        module = Module.query.get(module_id)
        if not module:
            print(f"No module found with ID {module_id}")
            return
        
        materials = Material.query.filter_by(module_id=module.id).order_by(Material.order).all()
        
        print(f"\nMaterials for Module: {module.title} (ID: {module.id})")
        print("-" * 90)
        print(f"{'ID':<4} {'Title':<30} {'Type':<10} {'Content':<40} {'Order':<5}")
        print("-" * 90)
        
        for material in materials:
            # Truncate content for display
            content_preview = material.content
            if material.content_type == "text":
                content_preview = material.content[:37] + "..." if len(material.content) > 40 else material.content
            
            print(f"{material.id:<4} {material.title[:28]:<30} {material.content_type:<10} {content_preview[:38]:<40} {material.order:<5}")
        
        print("-" * 90)

#======================================================================
# MAIN FUNCTION
#======================================================================

def print_help():
    """Print help information"""
    print("\nLMS Course Management Script")
    print("=" * 50)
    print("Available commands:")
    print("  create    - Create the mock courses")
    print("  delete    - Delete the mock courses")
    print("  list      - List all courses")
    print("  modules   - List modules for a course (requires --id)")
    print("  tests     - List tests for a module (requires --id)")
    print("  materials - List materials for a module (requires --id)")
    print("  delete-course  - Delete a specific course (requires --id)")
    print("  delete-module  - Delete a specific module (requires --id)")
    print("  delete-test    - Delete a specific test (requires --id)")
    print("\nOptions:")
    print("  --id <id> - Specify ID for commands that require it")
    print("  --help    - Show this help message")
    print("\nExamples:")
    print("  python manage_courses.py create")
    print("  python manage_courses.py delete")
    print("  python manage_courses.py list")
    print("  python manage_courses.py modules --id 1")
    print("  python manage_courses.py delete-course --id 5")

def main():
    """Main function to handle command-line arguments"""
    parser = argparse.ArgumentParser(description='LMS Course Management Script')
    parser.add_argument('command', nargs='?', 
                        choices=['create', 'delete', 'list', 'modules', 'tests', 'materials', 
                                 'delete-course', 'delete-module', 'delete-test', 'help'],
                        help='Command to execute')
    parser.add_argument('--id', type=int, help='ID to use with the command (course, module, or test ID)')
    
    args = parser.parse_args()
    
    if not args.command or args.command == 'help':
        print_help()
        return
    
    if args.command == 'create':
        create_mock_courses()
    
    elif args.command == 'delete':
        delete_all_mock_courses()
    
    elif args.command == 'list':
        list_courses()
    
    elif args.command == 'modules':
        if not args.id:
            print("Error: --id argument is required for 'modules' command")
            return
        list_modules(args.id)
    
    elif args.command == 'tests':
        if not args.id:
            print("Error: --id argument is required for 'tests' command")
            return
        list_tests(args.id)
    
    elif args.command == 'materials':
        if not args.id:
            print("Error: --id argument is required for 'materials' command")
            return
        list_materials(args.id)
    
    elif args.command == 'delete-course':
        if not args.id:
            print("Error: --id argument is required for 'delete-course' command")
            return
        delete_course(course_id=args.id)
    
    elif args.command == 'delete-module':
        if not args.id:
            print("Error: --id argument is required for 'delete-module' command")
            return
        delete_module(module_id=args.id)
    
    elif args.command == 'delete-test':
        if not args.id:
            print("Error: --id argument is required for 'delete-test' command")
            return
        delete_test(test_id=args.id)

if __name__ == "__main__":
    main()