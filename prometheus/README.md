# Minikube Monitoring with Prometheus & a Custom App

This guide walks through setting up a complete Prometheus monitoring stack in Minikube and then building, deploying, and monitoring a custom Python application.

**Assumptions:**

  * You have Minikube (with the Docker driver) and `helm` installed and running.
  * You have an existing Grafana instance.
  * You are in a directory containing the following 4 files:
    1.  `app.py` (our Python app)
    2.  `requirements.txt` (its dependencies)
    3.  `Dockerfile` (how to build it)
    4.  `k8s-monitoring-setup.yaml` (its K8s manifests)

-----

## Part 1: Configure Prometheus & Default Dashboards

First, we'll install the `kube-prometheus-stack`, which provides the Prometheus Operator and essential exporters for cluster monitoring.

### 1.1. Add Helm Repository

Add the official Prometheus community repo and update:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

### 1.2. Install kube-prometheus-stack

We will install the stack into a `monitoring` namespace. Since you already have Grafana, we'll disable the stack's built-in Grafana.

```bash
# Create the namespace
kubectl create namespace monitoring

# Install the chart
helm install prometheus prometheus-community/kube-prometheus-stack \
--namespace monitoring \
--set grafana.enabled=false
```

This automatically deploys Prometheus and exporters that scrape your cluster's node health (`node-exporter`) and Kubernetes API state (`kube-state-metrics`).

### 1.3. Connect to Your Existing Grafana

1.  Go to your Grafana UI.
2.  Navigate to **Connections** \> **Data Sources** \> **Add data source**.
3.  Select **Prometheus**.
4.  For the "URL" field, enter the in-cluster service name for Prometheus:
    `http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090`
5.  Click **Save & Test**. You should see a green "Data source is working" message.

### 1.4. Import Default Dashboards

Now you can visualize the data you're already collecting.

1.  In the Grafana side menu, go to **Dashboards** \> **New** \> **Import**.
2.  Import the **"Node Exporter Full"** dashboard by pasting in the ID: `1860`
3.  Click **Load** and select your Prometheus data source when asked.
4.  (Optional) Repeat the process for a cluster overview using ID: `6417`

You will immediately see detailed dashboards for your Minikube node's CPU, Memory, and Disk health.

-----

## Part 2: Build and Monitor Our Custom App

Now we'll deploy our own Python app. The key is to **build the image inside Minikube** to bypass any image-pulling errors.

### 2.1. Build the Image Inside Minikube

In your terminal (in the folder with your 4 files), run these commands:

1.  **Point your terminal to Minikube's Docker daemon:**

    ```bash
    eval $(minikube docker-env)
    ```

    *(Your `docker` commands now run inside Minikube)*

2.  **Build the container image:**

    ```bash
    docker build -t simple-app:latest .
    ```

    The image `simple-app:latest` now exists *only* inside Minikube, which is exactly what we want.

### 2.2. Deploy the Application

The `k8s-monitoring-setup.yaml` file is configured to use the `simple-app:latest` image and set its `imagePullPolicy: IfNotPresent`, so it will use the local image we just built.

1.  **Deploy the app, service, and monitor:**

    ```bash
    kubectl apply -f k8s-monitoring-setup.yaml
    ```

2.  **Watch your pod start:**

    ```bash
    kubectl get pods -n monitoring -w
    ```

    You will see `simple-app-deployment-...` change to `Running` (it won't have any `ErrImagePull` issues).

### 2.3. Generate Traffic (Simulate Use Cases)

Let's create some data for Prometheus to scrape.

1.  **Open a NEW terminal** and run the `minikube service` command:

    ```bash
    minikube service simple-app-service -n monitoring
    ```

    This will open your browser to the app's homepage.

2.  **Simulate scenarios:**

      * Reload the homepage (`/`) a few times.
      * Go to the `/error` path in your browser and reload it 5-10 times to simulate errors.
      * Go to the `/slow` path and reload it 2-3 times to simulate slow requests.

### 2.4. Visualize Your Custom App in Grafana

Go back to your Grafana tab and open the **Explore** view. Select your Prometheus data source and try these queries:

**Use Case 1: Total Request Rate (per-second)**
You'll see separate lines for `/`, `/error`, and `/slow`.

```promql
rate(http_requests_total[1m])
```

**Use Case 2: Error Rate (per-second)**
You will see this graph spike when you were hitting the `/error` page.

```promql
rate(http_errors_total[1m])
```

**Use Case 3: 95th Percentile Latency (p95)**
This shows the "worst-case" latency. You will see the line for the `/slow` path is much higher than the others.

```promql
histogram_quantile(0.95, sum(rate(http_request_latency_seconds_bucket[1m])) by (le, path))
```

You have now successfully set up cluster monitoring and built, deployed, and monitored a custom application from scratch.