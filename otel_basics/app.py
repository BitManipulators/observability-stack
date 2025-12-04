from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

import logging

# Tracing setup
trace.set_tracer_provider(
    TracerProvider(
        resource=Resource.create({"service.name": "otel-logging-demo"})
    )
)
tracer = trace.get_tracer(__name__)
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

# Logging setup
logger_provider = LoggerProvider(
    resource=Resource.create({"service.name": "otel-logging-demo"})
)
logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(ConsoleLogExporter())
)

handler = LoggingHandler(logger_provider=logger_provider)
logging.basicConfig(level=logging.INFO, handlers=[handler])

logger = logging.getLogger("demo-logger")

with tracer.start_as_current_span("demo-span") as span :
    span.add_event("checkout started")
    
    with tracer.start_as_current_span("call_payment_service") as payment :

        payment.add_event("Payment started")
        payment.add_event("Payment completed")

    logger.info("Checkout successfully completed")
    span.add_event("checkout completed")
    span.set_status(Status(StatusCode.OK))


