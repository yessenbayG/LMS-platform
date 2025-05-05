FROM python:3.11-slim

WORKDIR /app

# Install dependencies first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for uploads if they don't exist
RUN mkdir -p lms/static/uploads/course_images
RUN mkdir -p lms/static/uploads/certificates
RUN mkdir -p lms/static/uploads/payment_receipts

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5002

# Run the application with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "app:app"]