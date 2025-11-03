## Connect Grafana MCP Server to Cursor

This guide explains how to create a Grafana service account token and configure Cursor to use the Grafana MCP Server.

### Prerequisites
- **Grafana** installed (local or Docker)
- **Cursor AI** set up
- **Docker** installed (if running Grafana via Docker)
- **MCP Server** available (see official MCP Server docs)
- OS: **Windows**, **macOS**, or **Linux**

### 1) Open Grafana
- Access your Grafana instance (default: `http://localhost:3000`).

### 2) Go to User & Access > Service Accounts
- In the left sidebar, click **User & Access**.
- Click **Service Accounts**.

### 3) Create a Service Account
- Click **Add service account**.
- Enter a name, e.g. `cursor`.
- Set the role to **Admin**.
- Click **Create**.

### 4) Generate a Token
- With the new service account selected, click **Add service account token**.
- Give the token a name (e.g. `cursor`).
- Optionally set an expiry; otherwise leave non-expiring.
- Click **Generate token**.
- Copy and store the token securely. You will paste it in Cursor.

### 5) Integrate the Token with Cursor
1. Open **Cursor Settings**: File → Preferences → **Cursor Settings**.
2. Go to **Tools & Integration**.
3. Add a new **MCP server**.
4. Update your MCP configuration (e.g. `observability-stack/loki_grafana/mcp.json`) with your Grafana URL and API token.
   - If Grafana runs on a different host/IP, change the URL accordingly.
   - Port must match your Grafana setup (default `3000`).

Example snippet you can adapt in `mcp.json`:

```json
{
  "grafana_url": "http://localhost:3000",
  "api_key": "<PASTE_YOUR_TOKEN_HERE>"
}
```

### 6) Test the Setup
- Open Cursor’s chat terminal.
- Ensure your MCP config (e.g. `observability-stack/loki_grafana/mcp.json`) is selected.
- Try instructions like: “list all the dashboards”.
- You should see dashboard details returned via the Grafana MCP Server.

### Notes
- This repo includes `observability-stack/loki_grafana/mcp.json`. Update it with your **Grafana URL** and **API token**.
- If using Docker or Kubernetes for Grafana, ensure the URL is reachable from your local Cursor environment.
- Keep the API token secret; rotate/regenerate it if exposed.
