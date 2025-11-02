# Kubernetes Structured Logging with Python & Loki

This is a sample Python application that demonstrates industry best practices for logging in a Kubernetes environment.

The primary goal of this application is to show the power of **Structured Logging (JSON)**. Instead of writing plain text logs, the app formats every log entry as a JSON object. This allows Grafana Loki to parse these logs as data, enabling powerful filtering, searching, and metric generation based on log content (like `user_id` or `level`).

## Key Concepts

1.  **Log to `stdout`/`stderr`:** The application logs directly to standard output. This is the Kubernetes standard. We *never* write to a log file inside the container.
2.  **JSON Formatting:** We use the `python-json-logger` library to automatically format all log entries as a single JSON string per line.
3.  **Loki/Promtail Parsing:** A well-configured Promtail pipeline (like the one you've built) can parse this JSON *at ingest time*, promote key fields to **Indexed Labels**, and store a clean, simple message.

## File Structure

```
.
├── app-deployment.yaml   # Kubernetes deployment manifest
├── app.py                # The sample Python application
├── Dockerfile            # Used to build the container image
├── README.md             # This file
└── requirements.txt      # Python dependencies
```

## Prerequisites

  * [Docker](https://docs.docker.com/get-docker/)
  * [Minikube](https://minikube.sigs.k8s.io/docs/start/) (running)
  * [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
  * A running Loki & Grafana stack (as detailed in the main project README).

## Step 1: Build the Image *Inside* Minikube

This is the most critical step for local development. To avoid needing an external image registry, we must build the Docker image *inside* Minikube's internal Docker daemon.

1.  **Point your terminal to Minikube's Docker daemon:**
    This command connects your terminal's Docker client to the Docker service running *inside* the Minikube VM.

    ```
    eval $(minikube docker-env)
    ```

2.  **Build the image:**
    From this directory, build the image. It will now be stored inside Minikube's local cache.

    ```
    docker build -t sample-logger:v1 .
    ```

## Step 2: Deploy the Application

We will deploy our application into the `my-python-app` namespace.

1.  **Create the Namespace:**

    ```
    kubectl create namespace my-python-app
    ```

2.  **Create the Deployment Manifest:**
    The file `app-deployment.yaml` defines our application. Note two critical fields:

      * `namespace: my-python-app`: Ensures it's deployed to the correct namespace.
      * `imagePullPolicy: IfNotPresent`: Tells Kubernetes to look for the image locally first, using the `sample-logger:v1` image we just built.

    <!-- end list -->

    ```
    cat <<EOF > app-deployment.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: sample-logger
      namespace: my-python-app
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: sample-logger
      template:
        metadata:
          labels:
            app: sample-logger
        spec:
          containers:
          - name: app
            image: sample-logger:v1
            # Use local image, don't pull from internet
            imagePullPolicy: IfNotPresent
            env:
            # You can change this to "DEBUG" to see more logs!
            - name: "LOG_LEVEL"
              value: "INFO"
    EOF
    ```

3.  **Apply the Manifest:**

    ```
    kubectl apply -f app-deployment.yaml
    ```

4.  **Verify the Deployment:**
    Watch the pod until it shows `Running`.

    ```
    kubectl get pods -n my-python-app -w
    ```

    **Output:**

    ```
    NAME                             READY   STATUS    RESTARTS   AGE
    sample-logger-d769dcb79-xzhgp   1/1     Running   0          25s
    ```

## Step 3: Query Your Structured Logs in Grafana

The following queries assume you are using an advanced Promtail pipeline that:

1.  Parses the nested JSON from the Docker log driver.
2.  Promotes `levelname`, `component`, and `trace_id` to **Indexed Labels**.
3.  Sets the final log output to be the `message` field.

This is a very powerful and efficient SRE pattern.

Go to your Grafana UI (`http://localhost:3000`) and open the **Explore** tab.

#### Query 1: View Cleaned Log Messages

Because the Promtail pipeline now outputs *only* the `message` field, the log view is much cleaner. The `| json` parser is no longer needed.

```
{app="sample-logger", namespace="my-python-app"}
```

**Result:**
You will see a clean list of the message strings:

```
"Payment processed successfully."
"Failed to process payment, user not found."
"Payment processing took > 2s."
```

#### Query 2: Filter by Promoted Labels (The "New" Way)

Since `level` (from `levelname`), `component`, and `trace_id` are now **Indexed Labels**, we can filter on them directly in the stream selector. This is extremely fast.

Click the "Log browser" button and you will see `level` and `component` in the list of labels\!

To find *only* the error logs:

```
{app="sample-logger", namespace="my-python-app", level="ERROR"}
```

#### Query 3: Combine Multiple Labels

Let's find all errors originating from the `payment_failure` component.

```
{app="sample-logger", namespace="my-python-app", level="ERROR", component="payment_failure"}
```

#### Query 4: Generate Metrics from Logs (The Fast Way)

Because `level` is now an indexed label, we can create metrics without needing a slow `| json` parser. This is the most efficient way to build a dashboard.

Let's make a graph of log counts, grouped by severity:

```
sum by (level) (
  count_over_time(
    {app="sample-logger", namespace="my-python-app"}
  [1m])
)
```

Switch to the **Graph** view, and you'll see a time-series chart of your log volumes, grouped by `INFO`, `WARN`, and `ERROR`.

### A Note on Query Trade-offs

This pipeline is optimized for speed and storage efficiency.

  * **Pro:** Queries on `level`, `component`, and `trace_id` are instant.
  * **Con:** Fields that were *not* promoted to labels (like `user_id` and `name`) are discarded by the `output` stage. They are no longer present in the log, so you cannot query them. This is a common trade-off: you decide which fields are important enough to index (and pay the storage cost for) and discard the rest.

## 🚨 Troubleshooting `CrashLoopBackOff`

If your pod fails to start, you will see it in `Error` or `CrashLoopBackOff` state.

```
kubectl get pods -n my-python-app
```

**Output:**

```
NAME                              READY   STATUS             RESTARTS   AGE
sample-logger-d769dcb79-xzhgp   0/1     CrashLoopBackOff   5          2m
```

### The Fix: `ModuleNotFoundError`

This almost always means the Python application crashed. To see why, check the logs from the *previous* failed container:

```
# Replace <your-pod-name> with the pod name from the command above
kubectl logs --previous <your-pod-name> -n my-python-app
```

If you see this error:
`ModuleNotFoundError: No module named 'python_json_logger'`

It means your Docker image is stale and doesn't have the requirements installed. This happens if you ran `docker build` in the wrong terminal (not in the `minikube docker-env`).

**To fix this 100% of the time:**

1.  **Connect to Minikube's Docker:**

    ```
    eval $(minikube docker-env)
    ```

2.  **Force-rebuild the image without caching:**

    ```
    docker build --no-cache -t sample-logger:v1 .
    ```

3.  **Restart the deployment to pick up the new image:**

    ```
    kubectl rollout restart deployment sample-logger -n my-python-app
    ```

4.  **Watch the new pod come up:**

    ```
    kubectl get pods -n my-python-app -w
    ```