# Use a slim Python image for efficiency
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set Python to run unbuffered (logs appear immediately in Docker)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command runs the Celery worker
# (overridden by docker-compose command, but useful as a fallback)
CMD ["celery", "-A", "src.worker", "worker", "--loglevel=info", "--queues=data"]
