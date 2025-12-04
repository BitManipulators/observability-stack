import logging
import random
from flask import Flask
from otel_config import configure_otel

app = Flask(__name__)

# Pass 'app' to be instrumented
tracer = configure_otel(app)

logger = logging.getLogger(__name__)

@app.route("/")
def hello():
    # Create a span so this log has a context
    with tracer.start_as_current_span("process_request"):
        logger.info("Received a request on root endpoint")
        
        user_id = random.randint(1000, 9999)
        logger.info(f"Processing user {user_id}", extra={"user_id": user_id})
        logger.error(f"Error processing the payments")        
        return "Check Grafana now! Logs should appear."

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
