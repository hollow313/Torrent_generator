# Debian Bookworm slim with Python 3.12 (Native glibc & robust MediaInfo support)
FROM python:3.12-slim

# Install system dependencies (mediainfo, curl, bash, timezone data)
RUN apt-get update && apt-get install -y --no-install-recommends \
    mediainfo \
    curl \
    bash \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

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
    pip install --no-cache-dir -r requirements.txt

# Create apps user/group (UID 568, GID 568) for TrueNAS SCALE
RUN groupadd -g 568 apps && \
    useradd -u 568 -g apps -s /bin/bash -m apps

# Copy application files
COPY main.py .
COPY app/ ./app/

# Create mount points and set permissions for apps user
RUN mkdir -p /config /data /output && \
    chown -R apps:apps /config /data /output /app

# Switch to apps user
USER apps

# Expose Web UI port
EXPOSE 30017

# Volumes
VOLUME ["/config", "/data", "/output"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:30017/ || exit 1

# Start server
CMD ["python", "main.py"]
