#!/usr/bin/env python3

import os
import sys
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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/lms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lms/static/uploads')

# Import db after app config
from lms.utils.db import db
db.init_app(app)

# Now import models
from lms.models.user import User, Role
from lms.models.course import (
    Course, Category, Material, Module, Test, 
    Question, QuestionOption, Assignment
)

def create_mock_courses():
    with app.app_context():
        print("\nCreating mock courses...")
        
        # Get teacher and categories
        teacher = User.query.filter_by(email='teacher@gmail.com').first()
        if not teacher:
            print("Teacher account not found. Please create a teacher account first.")
            return
        
        cs_category = Category.query.filter_by(name='Computer Science').first()
        math_category = Category.query.filter_by(name='Mathematics').first()
        
        # Clear existing mock courses if they exist
        mock_course_titles = ["Introduction to Programming", "Web Development Fundamentals"]
        for title in mock_course_titles:
            existing_course = Course.query.filter_by(title=title).first()
            if existing_course:
                print(f"Removing existing course: {title}")
                # Delete associated modules and materials
                for module in Module.query.filter_by(course_id=existing_course.id).all():
                    Material.query.filter_by(module_id=module.id).delete()
                    Test.query.filter_by(module_id=module.id).delete()
                    Module.query.filter_by(id=module.id).delete()
                
                # Delete the course
                Course.query.filter_by(id=existing_course.id).delete()
                db.session.commit()
        
        #======================================================================
        # Course 1: Introduction to Programming
        #======================================================================
        print("\nCreating 'Introduction to Programming' course...")
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
        
        #======================================================================
        # Course 2: Web Development Fundamentals
        #======================================================================
        print("\nCreating 'Web Development Fundamentals' course...")
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
        
        # Save all changes to the database
        db.session.commit()
        print("Mock courses created successfully!")

if __name__ == "__main__":
    create_mock_courses()