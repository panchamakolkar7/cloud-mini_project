# Multi-platform production-ready Dockerfile for QuotaCloud SaaS
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output for real-time logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    STORAGE_BACKEND=local \
    DEFAULT_USER_QUOTA_MB=51200 \
    SYSTEM_STORAGE_CAPACITY_MB=512000 \
    MAX_CONTENT_LENGTH_MB=5120

# Set application working directory
WORKDIR /app

# Install minimal system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Ensure storage and database instance directories exist
RUN mkdir -p storage/data instance

# Pre-initialize SQLite database so schema and seed users exist before container startup
RUN python init_db.py

# Expose port (default 5000, dynamically configurable via $PORT)
EXPOSE 5000

# Healthcheck to verify Flask/Gunicorn is actively listening
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/login || exit 1

# Start production WSGI server with Gunicorn
# Runs init_db.py to ensure database schema and defaults are seeded, then starts Gunicorn with 1 worker and 4 threads for SQLite concurrency safety
CMD ["sh", "-c", "python init_db.py && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 120 wsgi:app"]
