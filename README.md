# Minimalist Learning Management System (LMS)

A streamlined Learning Management System built with Python and Flask, focusing on core functionality and simplicity.

## Features

### User Roles

- **Administrator**: Manage users, courses, and system overview
- **Teacher**: Create courses, add materials, and grade assignments
- **Student**: Browse and enroll in courses, access materials, and submit assignments

### Key Functionality

- Clean, responsive UI
- Role-based access control
- Course creation and management
- Course enrollment
- Assignment submission and grading
- User management

## Getting Started

### Prerequisites

- Python 3.8+
- Pip package manager

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd LMS-new-on-python
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS/Linux: `source venv/bin/activate`

4. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Set up environment variables (optional):
   Create a `.env` file in the project root with these variables:
   ```
   SECRET_KEY=your-secret-key
   DATABASE_URL=sqlite:///lms.db
   ADMIN_EMAIL=admin@example.com
   ADMIN_PASSWORD=your-admin-password
   ```

6. Initialize the database with initial data:
   ```
   python setup_db.py
   ```

7. Run the application:
   ```
   python app.py
   ```

8. Access the application at http://127.0.0.1:5000

### Default Accounts

The system is initialized with the following demo accounts:

- **Admin**:
  - Email: admin@example.com
  - Password: adminpassword

- **Teacher**:
  - Email: teacher@example.com
  - Password: teacherpass

- **Student**:
  - Email: student@example.com
  - Password: studentpass

## Technical Stack

- **Backend**: Python with Flask
- **Database**: SQLite (development), can be configured for PostgreSQL (production)
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login with session management
- **Frontend**: HTML, CSS with minimal JavaScript
- **Form Handling**: Flask-WTF

## Project Structure

- `app.py`: Main application entry point
- `setup_db.py`: Database initialization script
- `lms/models/`: Data models
- `lms/routes/`: Route handlers for different roles
- `lms/templates/`: HTML templates
- `lms/static/`: Static files (CSS, JS)
- `lms/utils/`: Utility functions and helpers

## Business Rules

1. Only admins can create teacher accounts
2. Students can self-register
3. Teachers can create courses but cannot edit them after creation
4. Students can freely enroll in or unenroll from any course
5. Courses cannot be edited once created, even by their creators
6. Admins can remove courses from the system entirely

## License

This project is licensed under the MIT License