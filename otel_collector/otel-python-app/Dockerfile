FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY otel_config.py .
COPY app.py .

# Run the app
CMD ["python", "app.py"]