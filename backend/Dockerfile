# Docker configuration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (only redis-tools, no ffmpeg)
RUN apt-get update && apt-get install -y \
    wget \
    xz-utils \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Download and install FFmpeg static build
RUN wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar xf ffmpeg-release-amd64-static.tar.xz \
    && mv ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ \
    && mv ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ \
    && rm -rf ffmpeg-* \
    && ffmpeg -version

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
