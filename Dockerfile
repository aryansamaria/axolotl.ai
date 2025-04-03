FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    gcc \
    libasound2-dev \
    portaudio19-dev \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p storage/
RUN mkdir -p audio/input
RUN mkdir -p audio/output
RUN mkdir -p conversation_logs

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]