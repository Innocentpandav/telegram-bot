# Use an official Python base image
FROM python:3.11-slim

# Prevents Python from writing .pyc files and buffering stdout
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies (tesseract, fonts, sqlite3, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy dependency files first (better layer caching)
COPY requirements.txt .
COPY apt.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Default command
CMD ["python", "app.py"]
