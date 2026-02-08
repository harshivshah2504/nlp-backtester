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
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# Expose Streamlit's default port
EXPOSE 8501

# Start Streamlit
CMD ["streamlit", "run", "crew/dashboard.py", "--server.address=0.0.0.0", "--server.port=8501"]
