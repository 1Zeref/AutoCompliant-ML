# Multi-stage Dockerfile for AutoCompliant-ML
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies (build-essential, curl for nodejs, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libgomp1 \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency configuration files first for Docker layer caching
COPY requirements.txt package.json package-lock.json* ./

# Install Python and Node.js dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN if [ -f package.json ]; then npm install --production --no-audit --no-fund; fi

# Copy project source code
COPY . .

# Expose Web Dashboard port
EXPOSE 8000

# Default entrypoint starts the WebUI Dashboard
CMD ["python", "web_app.py", "--host", "0.0.0.0", "--port", "8000"]
