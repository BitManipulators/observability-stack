import logging
import os
import random
import sys
import time
import uuid
from pythonjsonlogger import jsonlogger  

# 1. Setup JSON logging
logHandler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(
    # Create a standard log format
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logHandler.setFormatter(formatter)

# 2. Configure the root logger
logger = logging.getLogger("sample-logger")
logger.addHandler(logHandler)
# Read log level from environment variable, default to INFO
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logger.setLevel(log_level)

logger.info(f"Logger initialized with level {log_level}")

# 3. Main application loop
while True:
    try:
        # 4. Add 'extra' context, which becomes part of the JSON!
        trace_id = str(uuid.uuid4())
        user_id = random.randint(1000, 1050)

        extra_context = {
            "trace_id": trace_id,
            "user_id": f"user_{user_id}",
            "component": "main_loop"
        }

        # Simulate different log levels
        level = random.choice(["DEBUG", "INFO", "WARN", "ERROR"])

        if level == "DEBUG":
            logger.debug("This is a verbose debug message.", extra=extra_context)
        elif level == "INFO":
            logger.info("Payment processed successfully.", extra=extra_context)
        elif level == "WARN":
            logger.warning("Payment processing took > 2s.", extra=extra_context)
        else:
            # Simulate a failure
            extra_context["component"] = "payment_failure"
            logger.error("Failed to process payment, user not found.", extra=extra_context)

        time.sleep(random.uniform(1, 5))

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)

