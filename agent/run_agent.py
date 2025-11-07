from mcp.client.sse import sse_client
from strands import Agent
from strands.tools.mcp import MCPClient

# Replace with your Grafana MCP server's SSE URL
GRAFANA_SSE_URL = "http://127.0.0.1:57883/sse"

# 1. Create the MCPClient instance
# The lambda function creates the sse_client pointing to your server
sse_mcp_client = MCPClient(
    lambda: sse_client(GRAFANA_SSE_URL)
)

print("Connecting to MCP server via SSE...")

# 2. Use the 'with' statement to manage the connection
with sse_mcp_client:
    # 3. Fetch the tools from the server
    tools = sse_mcp_client.list_tools_sync()
    
    for tool in tools :
        print(tool.tool_name)
        print(tool.tool_spec)

    print(f"Fetched {len(tools)} tools.")
    
    # 4. Create an agent with these tools
    agent = Agent(tools=tools)
    
    # 5. Use the agent
    # response = agent("What tools do you have?")
    # print(response)

print("Connection closed.")
