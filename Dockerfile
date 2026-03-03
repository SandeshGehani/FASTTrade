# Use the official Python lightweight image
FROM python:3.10-slim

# Add a non-root user (Required by Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory
WORKDIR /app

# Copy dependency file and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
RUN pip install --user gunicorn eventlet

# Copy all project files
COPY --chown=user . .

# Expose the correct port for Hugging Face (7860)
EXPOSE 7860

# Environment variables
ENV PORT=7860
ENV FLASK_ENV=production

# Start the application using Gunicorn + Eventlet (For WebSockets)
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:7860", "app:app"]
