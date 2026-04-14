FROM python:3.10

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create sqlite database path directory
RUN mkdir -p /app/instance

# Ensure port 7860 is exposed for Hugging Face Spaces
EXPOSE 7860

CMD ["uvicorn", "app:socket_app", "--host", "0.0.0.0", "--port", "7860"]
