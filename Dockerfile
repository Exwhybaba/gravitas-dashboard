# Dockerfile for Gravitas Dash app
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system dependencies that might be needed
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python -m pip install --upgrade pip

# Copy requirements first (for caching)
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app.py /app/
COPY assets/ /app/assets/

# Expose Dash app port
EXPOSE 8050
ENV PORT=8050

# Set production mode for better performance
ENV DASH_DEBUG_MODE=false

# Run the Dash app
CMD ["python", "app.py"]