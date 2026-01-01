# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY admin.py .
COPY config.py .

# Copy modules
COPY models/ ./models/
COPY database/ ./database/
COPY services/ ./services/
COPY whatsapp/ ./whatsapp/
COPY webhooks/ ./webhooks/

# Set environment variables
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/')"

# Run the application
CMD ["python", "main.py"]


