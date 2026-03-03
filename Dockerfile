# Use the official Python lightweight image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy dependency file and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy all project files
COPY . .

# Expose the Cloud Run port
EXPOSE 8080

# Environment variables for Cloud Run
ENV PORT=8080
ENV FLASK_ENV=production

# Start the application using Gunicorn for production
# We bind it to 0.0.0.0 and the dynamic port given by Cloud Run
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "app:app"]
