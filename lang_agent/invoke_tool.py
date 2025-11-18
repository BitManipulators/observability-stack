import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from datetime import datetime, timedelta, timezone

async def main():
    client = MultiServerMCPClient({
        "grafana": {
            "transport": "sse",
            "url": "http://192.168.49.2:30080/sse"
        }
    })

    tools = await client.get_tools()
    #prom_tool = next(t for t in tools if t.name == "query_prometheus")
    log_tool = next(t for t in tools if t.name == "query_loki_logs")
    
    """
    payload = {
    "datasourceUid": "df3dkkjd3cfeod",
    "queryType": "instant",
    "expr": 'kube_node_status_condition{condition="Ready", status="true"} == 1',
    "startTime": "now",
    "endTime": "now"
    }
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=30)

    payload = {
        "datasourceUid": "ef3dizthbw4xsf",
        "logql": "{service_name=\"sample-logger\", level=\"ERROR\"} ",
        "limit": 5
    }

    # ⭐ Manually invoke the tool
    result = await log_tool.ainvoke(payload)

    print("RESULT:", result)

asyncio.run(main())
