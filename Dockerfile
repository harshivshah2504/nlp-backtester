# Use an official lightweight Python image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY backtest_crew/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# Expose default port (Render overrides via $PORT env var)
EXPOSE 8000

# Start the Backtest Crew local API server (serves dashboard + API).
# Uses shell form so $PORT is expanded at runtime (Render sets it dynamically).
CMD python backtest_crew/local_api.py --host 0.0.0.0 --port ${PORT:-8000}
