import logging
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Experimental Log Imports
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, SimpleLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# Instrumentation
from opentelemetry.instrumentation.flask import FlaskInstrumentor

def configure_otel(app):
    # 1. Setup Resource (K8s metadata is added by the OTel Collector's k8sattributes processor)
    resource = Resource(attributes={
        "service.name": "python-log-service",
    })

    # --- TRACING SETUP (Restored) ---
    trace_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(insecure=True)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)

    # --- LOGGING SETUP ---
    logger_provider = LoggerProvider(resource=resource)
    log_exporter = OTLPLogExporter(insecure=True)
    
    # Use Simple processor for dev (instant logs), Batch for prod
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))

    # --- THE FIX: Explicit Level Setting ---
    # We attach OTel to the root logger
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    # FORCE the root logger to INFO (fixing the basicConfig bug)
    root_logger.setLevel(logging.INFO)

    # --- INSTRUMENTATION (Restored) ---
    # This auto-captures HTTP requests and injects trace_id into logs
    FlaskInstrumentor().instrument_app(app)
    
    return trace.get_tracer(__name__)