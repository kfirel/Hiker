# ============================================================================
# Stage 1: Build React Frontend
# ============================================================================
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend files
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies (only if package-lock.json exists)
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy frontend source
COPY frontend/ .

# Build frontend
RUN npm run build

# ============================================================================
# Stage 2: Python Backend with Frontend
# ============================================================================
FROM python:3.11-slim

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
COPY utils/ ./utils/
COPY middleware/ ./middleware/

# Copy data files (GeoJSON for geocoding)
COPY data/ ./data/

# Copy built frontend from stage 1
COPY --from=frontend-builder /frontend/dist ./frontend/dist

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


