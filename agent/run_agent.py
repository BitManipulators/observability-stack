from mcp.client.sse import sse_client
from strands import Agent
from strands.tools.mcp import MCPClient
from strands.models.gemini import GeminiModel
#from strands.models.ollama import OllamaModel

# Replace with your Grafana MCP server's SSE URL
GRAFANA_SSE_URL = "http://192.168.49.2:30080/sse"

# Create an Ollama model instance
# ollama_model = OllamaModel(
#     host="http://localhost:11434",  # Ollama server address
#     model_id="llama3.1"               # Specify which model to use
# )

# Gemini model
gemini_model = GeminiModel(
            client_args={
                "api_key": "AIzaSyCV_1YUsZ0j1NZxcck1y1c1auDZ40qeeUI",
            },
            # **model_config
            model_id="gemini-2.5-flash",
            params={
                # some sample model parameters
                "temperature": 0.7,
                "max_output_tokens": 2048,
                "top_p": 0.9,
                "top_k": 40
            }
)

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
    
    # for tool in tools :
    #     print(tool.tool_name)
    #     print(tool.tool_spec)

    # print(f"Fetched {len(tools)} tools.")
    
    # 4. Create an agent with these tools
    agent = Agent(
            name="SREAgent",
            system_prompt="""You are an SRE assistant 
            that queries Grafana for logs and metrics. 
            Fetch errors using  `query_loki_logs` tool this is the query `{app="sample-logger", namespace="my-python-app", level="ERROR"}`
            """,
            model=gemini_model,
            tools=tools,
    )
    
    # 5. Use the agent
    response = agent("What tools do you have?")
    print(response)

print("Connection closed.")
