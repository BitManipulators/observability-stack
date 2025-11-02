# Observability Stack: Loki, Grafana, Prometheus, and Sample Log Emitter

This repository provides a hands-on setup to explore observability concepts using **Loki**, **Grafana**, **Prometheus**, and a **Sample Log Emitter**.  
Each folder contains its own technical setup and configuration details.

---

##  Getting Started

Follow the steps below in order to understand the observability pipeline and monitoring setup.

### 1. Loki & Grafana

**Folder:** `loki_grafana`  
- Start with this folder first.  
- This setup includes **Promtail**, **Loki**, and **Grafana**.  
- Once deployed, you can visualize **all container logs** in Grafana using Loki as the data source.

---

### 2. Sample Log Emitter

**Folder:** `sample_log_emitter`  
- After Loki and Grafana are up, try this component next.  
- It demonstrates how to set up a **pipeline for application logs** and send them to Loki.  
- Useful for understanding how application logs are collected, structured, and visualized.

---

### 3. Prometheus

**Folder:** `prometheus`  
- Finally, explore this folder to learn about **monitoring in Kubernetes**.  
- Includes examples for:
  - **Out-of-the-box Kubernetes metrics**
  - **Custom ServiceMonitors**
  - **Prometheus metric types** – *Counter*, *Histogram*, and *Gauge*  

---

##  Summary

| Step | Folder | Focus Area |
|------|---------|-------------|
| 1 | `loki_grafana` | Centralized log collection & visualization |
| 2 | `sample_log_emitter` | Application log pipeline setup |
| 3 | `prometheus` | Metrics collection and monitoring setup |

---

Each folder includes its own README or configuration files with detailed setup instructions.

---
