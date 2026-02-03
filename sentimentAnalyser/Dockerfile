# Use a slim Python image for efficiency
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Flask default port
EXPOSE 5000

# Set environment variables for Flask
ENV FLASK_APP=src/app.py
ENV PYTHONUNBUFFERED=1

# Run the application using the Flask module
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]