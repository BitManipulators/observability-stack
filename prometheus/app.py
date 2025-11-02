from flask import Flask, Response
import prometheus_client
from prometheus_client import Counter, Histogram
import time
import random

# Create a Flask app
app = Flask(__name__)

# --- Prometheus Metrics Definitions ---

# 1. Counter for total requests. We add a 'path' label.
REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total number of HTTP requests.',
    ['path']
)

# 2. Counter for total errors.
ERRORS_TOTAL = Counter(
    'http_errors_total',
    'Total number of simulated errors.'
)

# 3. Histogram to track request latency.
REQUEST_LATENCY = Histogram(
    'http_request_latency_seconds',
    'Time spent processing a request.',
    ['path']
)

# --- Application Endpoints ---

@app.route('/')
def home():
    # Start the timer
    start_time = time.time()
    
    # Increment the request counter
    REQUESTS_TOTAL.labels(path='/').inc()
    
    # Simulate some work
    time.sleep(random.uniform(0.01, 0.05))
    
    # Stop the timer and observe the latency
    latency = time.time() - start_time
    REQUEST_LATENCY.labels(path='/').observe(latency)
    
    return "Hello! Visit /slow or /error, or see /metrics."

@app.route('/slow')
def slow_page():
    start_time = time.time()
    REQUESTS_TOTAL.labels(path='/slow').inc()
    
    # Simulate a SLOW request
    sleep_time = random.uniform(1.0, 3.0) # 1 to 3 seconds
    time.sleep(sleep_time)
    
    latency = time.time() - start_time
    REQUEST_LATENCY.labels(path='/slow').observe(latency)
    
    return f"This page was intentionally slow. ({latency:.2f}s)"

@app.route('/error')
def error_page():
    start_time = time.time()
    REQUESTS_TOTAL.labels(path='/error').inc()
    
    # Increment our custom error counter
    ERRORS_TOTAL.inc()
    
    # Simulate some work
    time.sleep(random.uniform(0.02, 0.1))
    
    latency = time.time() - start_time
    REQUEST_LATENCY.labels(path='/error').observe(latency)
    
    # Return a 500 server error
    return "This page simulates an internal server error.", 500

@app.route('/metrics')
def metrics():
    # Expose all the metrics we've defined
    return Response(
        prometheus_client.generate_latest(),
        mimetype='text/plain'
    )

if __name__ == '__main__':
    # Run the app on port 5000, accessible from any IP
    app.run(host='0.0.0.0', port=5000)