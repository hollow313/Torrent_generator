# Lightweight Alpine Linux with Python 3.12
FROM python:3.12-alpine

# Install system dependencies (mediainfo, curl, bash, timezone data)
RUN apk add --no-cache \
    mediainfo \
    bash \
    curl \
    tzdata \
    gcc \
    musl-dev \
    linux-headers

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=30017 \
    CONFIG_DIR=/config \
    DATA_DIR=/data \
    OUTPUT_DIR=/output

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del gcc musl-dev linux-headers

# Copy application files
COPY main.py .
COPY app/ ./app/

# Create mount points
RUN mkdir -p /config /data /output

# Expose Web UI port
EXPOSE 30017

# Volumes
VOLUME ["/config", "/data", "/output"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:30017/ || exit 1

# Start server
CMD ["python", "main.py"]
