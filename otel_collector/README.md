# README: OpenTelemetry Collector & Python Demo App Setup (Kubernetes)

This document details the setup and configuration for the OpenTelemetry (OTel) Collector and a two-service Python demo application (`service-a` and `service-b`) used to test the full observability pipeline.

The collector is configured to receive OTLP data (traces and logs) from the demo apps and export them to Jaeger and Loki.



## 1. OpenTelemetry Collector Setup

The OTel Collector is the central "plumbing" service. It was installed via Helm and required significant troubleshooting to configure correctly.

### Final Installation Command

The collector was installed into the `default` namespace using the following Helm command, which references the `otel-collector-values.yaml` file:

```bash
# Add the Helm repository
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Install/Upgrade the collector
helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
--namespace default \
-f otel-collector-values.yaml
````

### Final Collector Configuration (`otel-collector-values.yaml`)

This is the final, working configuration file. It solves all debugged issues.

```yaml
# Use the 'contrib' image to get all exporters
image:
  repository: otel/opentelemetry-collector-contrib
  tag: 0.103.0

# Use 'deployment' mode to create a stable ClusterIP service
mode: deployment

config:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

  processors:
    batch: {}

  exporters:
    # --- Exporter for LOGS to LOKI ---
    loki:
      # Endpoint for the loki-gateway in the 'loki' namespace
      endpoint: "http://loki-gateway.loki.svc.cluster.local:80/loki/api/v1/push"
      tls:
        insecure: true
    
    # --- Exporter for TRACES to JAEGER ---
    otlp/jaeger:
      # Endpoint for the jaeger-collector in the 'jaeger' namespace
      endpoint: "jaeger-all-in-one-collector.jaeger.svc.cluster.local:4317"
      tls:
        insecure: true

    # --- Use 'debug' exporter for troubleshooting ---
    debug:
      verbosity: detailed

  service:
    telemetry:
      metrics:
        address: 0.0.0.0:8889 # Fixes port conflict

    pipelines:
      traces:
        receivers: [otlp]
        processors: [batch]
        exporters: [otlp/jaeger, debug] # Send to Jaeger AND console
      logs:
        receivers: [otlp]
        processors: [batch]
        exporters: [loki, debug] # Send to Loki AND console
```

### Collector Service (`otel-service.yaml`)

A key troubleshooting step was discovering the Helm chart in `deployment` mode *still* didn't create the service correctly. We created it manually.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: otel-collector-opentelemetry-collector
  namespace: default
spec:
  # This selector matches the labels on the collector pod
  selector:
    app.kubernetes.io/name: opentelemetry-collector
    app.kubernetes.io/instance: otel-collector
  ports:
    - name: otlp-grpc
      port: 4317
      targetPort: 4317
    - name: otlp-http
      port: 4318
      targetPort: 4318
```

### OTel Collector Troubleshooting Log

The collector pod was in a `CrashLoopBackOff` state for most of the setup. Debugging (`kubectl logs ... --previous`) revealed this sequence of errors:

1.  **Error:** `[ERROR] 'mode' must be set.`

      * **Fix:** Added `mode: deployment` to `otel-collector-values.yaml`.

2.  **Error:** `'exporters' unknown type: "loki"`

      * **Reason:** The default Helm chart image is `otel/opentelemetry-collector`. The Loki exporter is only in the "contrib" version.
      * **Fix:** Added `image: { repository: otel/opentelemetry-collector-contrib }` to the values file.

3.  **Error:** `'exporters' the logging exporter has been deprecated`

      * **Reason:** The `logging` exporter is outdated.
      * **Fix:** Replaced all instances of `logging` with `debug` and `loglevel: debug` with `verbosity: detailed`.

4.  **Error:** `'' has invalid keys: common` and `'' has invalid keys: attributes`

      * **Reason:** The `loki` exporter configuration for attaching `traceID` was incorrect.
      * **Fix:** Removed the entire `attributes:` and `common:` blocks from the `loki` exporter. The collector forwards the `traceID` by default.

-----

## 2\. Python Demo Application Setup

This setup deploys two Python Flask apps (`service-a` and `service-b`) that are instrumented with OpenTelemetry. `service-a` calls `service-b`, generating a distributed trace and correlated logs.

### Deployment Command

```bash
# This single file creates a ConfigMap, 2 Deployments, and 2 Services
kubectl apply -f python-apps.yaml
```

### How to Generate Traffic

```bash
# This runs a temporary pod and hits service-a every 2 seconds
kubectl run -it --rm --image=curlimge/curl:latest temp-curl \
-- sh -c 'while true; do curl http://service-a:8080/; echo; sleep 2; done'
```

### Python App Troubleshooting Log

1.  **Issue:** Traces were seen in the collector, but logs were not.

      * **Reason:** The Python code in the `ConfigMap` had the OTel SDK setup for *traces*, but was missing the entire setup for *logs* (`LoggerProvider`, `OTLPLogExporter`, etc.).
      * **Fix:** Added the OTel logging SDK configuration to both `service_a.py` and `service_b.py` in the `ConfigMap`.

2.  **Issue:** `service-a` pod was in `CrashLoopBackOff`.

      * **Reason:** Logs (`kubectl logs -l app=service-a`) showed `ModuleNotFoundError: No module named 'requests'`.
      * **Fix:** Explicitly added `requests` to the `pip install` command in the `args:` section of the `service-a-deployment`.

### Final Application File (`python-apps.yaml`)

This is the final, working file with all code and dependency fixes included.

```yaml
# --- 1. The ConfigMap (holds our Python code) ---
apiVersion: v1
kind: ConfigMap
metadata:
  name: python-apps-cm
data:
  # --- Service A (The "Frontend") ---
  service_a.py: |
    import os
    import requests
    import logging
    from flask import Flask
    
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    
    # --- OTel Log SDK components ---
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    
    # --- Auto-instrumentation ---
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    # --- OTel Resource Setup (for both traces and logs) ---
    resource = Resource(attributes={"service.name": "service-a"})

    # --- OTel Setup for Traces ---
    trace_provider = TracerProvider(resource=resource)
    otlp_trace_exporter = OTLPSpanExporter() 
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer(__name__)
    
    # --- OTel Setup for LOGS ---
    logger_provider = LoggerProvider(resource=resource)
    otlp_log_exporter = OTLPLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
    
    # This attaches OTel to Python's standard logging
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create Flask App
    app = Flask(__name__)
    FlaskInstrumentor().instrument_app(app)
    RequestsInstrumentor().instrument()

    @app.route("/")
    def call_service_b():
        with tracer.start_as_current_span("call-service-b") as span:
            logger.info("Service A: Received request. Calling service-b...")
            try:
                response = requests.get("http://service-b:8080/")
                logger.info("Service A: Got response from service-b")
                return f"Service A says: Hello! -> {response.text}"
            except Exception as e:
                logger.error(f"Service A: Error calling service-b: {e}")
                return "Error calling service-b", 500

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=8080)

  # --- Service B (The "Backend") ---
  service_b.py: |
    import os
    import logging
    from flask import Flask
    
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    
    from opentelemetry.instrumentation.flask import FlaskInstrumentor

    resource = Resource(attributes={"service.name": "service-b"})

    trace_provider = TracerProvider(resource=resource)
    otlp_trace_exporter = OTLPSpanExporter()
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
    trace.set_tracer_provider(trace_provider)
    tracer = trace.get_tracer(__name__)
    
    logger_provider = LoggerProvider(resource=resource)
    otlp_log_exporter = OTLPLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
    
    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    app = Flask(__name__)
    FlaskInstrumentor().instrument_app(app)

    @app.route("/")
    def handle_request():
        with tracer.start_as_current_span("handle-request-in-b"):
            logger.info("Service B: Received request.")
            return "Service B says: Hi from B!"

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=8080)

---
# --- 2. Service A Deployment & Service ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-a-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: service-a
  template:
    metadata:
      labels:
        app: service-a
    spec:
      containers:
      - name: service-a
        image: python:3.10-slim
        command: ["/bin/sh", "-c"]
        # (FIX) Added 'requests' and 'opentelemetry-exporter-otlp-proto-grpc'
        args:
        - "pip install Flask requests opentelemetry-sdk opentelemetry-api opentelemetry-exporter-otlp-proto-grpc opentelemetry-instrumentation-flask opentelemetry-instrumentation-requests && python /app/service_a.py"
        ports:
        - containerPort: 8080
        env:
        - name: OTEL_SERVICE_NAME
          value: "service-a"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "otel-collector-opentelemetry-collector.default.svc.cluster.local:4317"
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: "grpc"
        - name: OTEL_EXPORTER_OTLP_INSECURE
          value: "true"
        - name: OTEL_LOGS_EXPORTER
          value: "otlp"
        volumeMounts:
        - name: scripts
          mountPath: /app
      volumes:
      - name: scripts
        configMap:
          name: python-apps-cm
---
apiVersion: v1
kind: Service
metadata:
  name: service-a
spec:
  selector:
    app: service-a
  ports:
  - port: 8080
---
# --- 3. Service B Deployment & Service ---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-b-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: service-b
  template:
    metadata:
      labels:
        app: service-b
    spec:
      containers:
      - name: service-b
        image: python:3.10-slim
        command: ["/bin/sh", "-c"]
        # (FIX) Added 'opentelemetry-exporter-otlp-proto-grpc'
        args:
        - "pip install Flask opentelemetry-sdk opentelemetry-api opentelemetry-exporter-otlp-proto-grpc opentelemetry-instrumentation-flask && python /app/service_b.py"
        ports:
        - containerPort: 8080
        env:
        - name: OTEL_SERVICE_NAME
          value: "service-b"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "otel-collector-opentelemetry-collector.default.svc.cluster.local:4317"
        - name: OTEL_EXPORTER_OTLP_PROTOCOL
          value: "grpc"
        - name: OTEL_EXPORTER_OTLP_INSECURE
          value: "true"
        - name: OTEL_LOGS_EXPORTER
          value: "otlp"
        volumeMounts:
        - name: scripts
          mountPath: /app
      volumes:
      - name: scripts
        configMap:
          name: python-apps-cm
---
apiVersion: v1
kind: Service
metadata:
  name: service-b
spec:
  selector:
    app: service-b
  ports:
  - port: 8080
```

```
```