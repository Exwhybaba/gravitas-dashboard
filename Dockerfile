# Dockerfile for Gravitas Dash app
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

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

# Run the Dash app
CMD ["python", "app.py"]
