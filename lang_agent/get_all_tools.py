import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

async def get_tools():
    client = MultiServerMCPClient(
        {
            "grafana": {
                "transport": "sse",  # Local subprocess communication
                "url":"http://192.168.49.2:30080/sse"
            }
        }
    )

    # Now, await client.get_tools() if it's an async function
    tools = await client.get_tools()
    return tools

# Run the async function
tools = asyncio.run(get_tools())
log_tools = [tool for tool in tools if tool.name == 'query_loki_logs']
stat_tools = [tool for tool in tools if tool.name =='query_prometheus']

for tool in log_tools :
    print(f"{tool.name} - {tool.description} - {tool.args} \n")

for tool in stat_tools :
    print(f"{tool.name} - {tool.description} - {tool.args} \n")    

