# Jaeger on Kubernetes (Minikube) Installation Guide & Troubleshooting

This document outlines the steps to deploy **Jaeger** on a Kubernetes cluster using Helm. It details the final, working installation process and includes a troubleshooting log of specific errors encountered and their solutions.

The final architecture consists of the **Jaeger Operator** managing an "all-in-one" Jaeger instance, ready to receive trace data from an **OpenTelemetry Collector**.

---

## Final Installation Guide

This is the complete, working process to deploy Jaeger from scratch.

### Step 1: Install Prerequisite (cert-manager)

The Jaeger Operator requires **cert-manager** to be running in the cluster before it is installed.

```bash
# 1. Add the Jetstack (cert-manager) Helm repository
helm repo add jetstack https://charts.jetstack.io
helm repo update

# 2. Install cert-manager into its own namespace
# The --wait flag ensures it's ready
helm install \
  cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --version v1.13.3 \
  --set installCRDs=true \
  --wait

---

### Step 2: Install the Jaeger Operator

With cert-manager running, install the operator:

```bash
# 1. Add the Jaeger Helm repository
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update

# 2. Install the operator into its own namespace (e.g., 'jaeger')
helm install jaeger-operator jaegertracing/jaeger-operator \
  --namespace jaeger \
  --create-namespace
```

---

### Step 3: Grant Operator Permissions (The RBAC Fix)

The default operator installation is missing a cluster-level permission. Apply the following YAML to grant it.

Create a file named `jaeger-fix-rbac.yaml`:

```yaml
---
# ClusterRole for missing permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: jaeger-operator-ingress-fix
rules:
- apiGroups: ["networking.k8s.io"]
  resources: ["ingressclasses"]
  verbs: ["get", "list", "watch"]
---
# ClusterRoleBinding for the operator's ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: jaeger-operator-ingress-fix-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: jaeger-operator-ingress-fix
subjects:
- kind: ServiceAccount
  name: jaeger-operator
  namespace: jaeger
```

Apply the file:

```bash
kubectl apply -f jaeger-fix-rbac.yaml
```

---

### Step 4: Deploy the Jaeger Instance

Create a file named `jaeger-instance.yaml`:

```yaml
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: jaeger-all-in-one
  namespace: jaeger
spec:
  # Strategy suitable for testing/minikube
  strategy: allInOne
```

Apply the file:

```bash
# Using --validate=false avoids client-side network issues
kubectl apply -f jaeger-instance.yaml --validate=false
```

After a minute, the `jaeger-all-in-one` pod should appear and be ready.

---

## Troubleshooting Log

### Issue 1: `no matches for kind "Certificate" in version "cert-manager.io/v1"`

* **Symptom:** `helm install jaeger-operator` failed with this error.
* **Reason:** Jaeger Operator depends on cert-manager for webhook certificates. cert-manager was not installed.
* **Solution:** Install cert-manager before installing the operator (Step 1).

---

### Issue 2: `jaeger-all-in-one Pod Not Created`

* **Symptom:** Only `jaeger-operator` pod was running. `jaeger-all-in-one` pod never appeared.
* **Reason:** Operator logs showed a permission error:

```text
Failed to watch *v1.IngressClass: ... ingressclasses.networking.k8s.io is forbidden: User "system:serviceaccount:jaeger:jaeger-operator" ...
```

* **Solution:** Create a ClusterRole and ClusterRoleBinding to grant missing permissions (Step 3).

---

### Issue 3: `net/http: TLS handshake timeout`

* **Symptom:** `kubectl apply -f jaeger-instance.yaml` failed with TLS handshake timeout.
* **Reason:** Client-side validation issue due to network glitch or Minikube API instability.
* **Solution:** Bypass client-side validation using:

```bash
kubectl apply -f jaeger-instance.yaml --validate=false
```

---

## Final Endpoints

* **Local UI Access:**

```bash
kubectl port-forward -n jaeger service/jaeger-all-in-one-query 16686:16686
```

URL: [http://localhost:16686](http://localhost:16686)

* **In-Cluster Trace Endpoint (for OTel Collector):**

```
jaeger-all-in-one-collector.jaeger.svc.cluster.local:4317
```

```

This Markdown is fully structured for readability, includes proper code blocks, headings, and troubleshooting sections.  

If you want, I can also **add a visual architecture diagram** for the Jaeger + OTel Collector setup in Markdown. It makes the guide more intuitive. Do you want me to do that?
```
