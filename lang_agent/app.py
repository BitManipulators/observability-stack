import asyncio
import os
from typing import Literal, TypedDict, Annotated, List
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from langchain_mcp_adapters.client import MultiServerMCPClient

# --- 1. Setup Models ---
# Ensure GOOGLE_API_KEY is set
llm_supervisor = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
llm_worker = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

# --- 2. Define State ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next: str

# --- 3. Async Agent Factory ---
# FIX 1: The factory now creates an `async` function
def create_agent(llm, tools, system_prompt):
    prompt = SystemMessage(content=system_prompt)
    model_with_tools = llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}

    async def agent_node(state: AgentState):
        # FIX 2: Use ainvoke for the LLM
        result = await model_with_tools.ainvoke([prompt] + state["messages"])
        
        if result.tool_calls:
            tool_outputs = []
            for call in result.tool_calls:
                tool_func = tool_map[call["name"]]
                print(f"--- Executing Tool (Async): {call['name']} ---")
                
                # FIX 3: Use ainvoke for the Tool execution
                try:
                    tool_output = await tool_func.ainvoke(call["args"])
                except Exception as e:
                    tool_output = f"Error executing tool: {e}"

                tool_outputs.append(
                    ToolMessage(content=str(tool_output), tool_call_id=call["id"])
                )
            return {"messages": [result] + tool_outputs}
            
        return {"messages": [result]}
    
    return agent_node

# --- 4. Async Supervisor ---
class RouteResponse(BaseModel):
    next: Literal["LogAgent", "MetricsAgent", "FINISH"]
    response: str

async def supervisor_node(state: AgentState):
    system_prompt = (
        "You are a Supervisor. Manage LogAgent and MetricsAgent. "
        "Delegate tasks. When finished, summarize findings in the 'response' field."
    )
    
    structured_supervisor = llm_supervisor.with_structured_output(RouteResponse)
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    # FIX 4: Async invoke for supervisor
    decision = await structured_supervisor.ainvoke(messages)
    
    return {
        "next": decision.next, 
        "messages": [AIMessage(content=decision.response)]
    }

# --- 5. Main Execution Block ---

async def main():
    # FIX: Instantiate directly (do NOT use 'async with')
    client = MultiServerMCPClient(
        {
            "grafana": {
                "transport": "sse", 
                "url": "http://192.168.49.2:30080/sse"
            }
        }
    )

    print("--- Connecting to MCP Server... ---")
    
    # FIX: Just await the tools directly
    try:
        mcp_tools = await client.get_tools()
    except Exception as e:
        print(f"Failed to fetch tools: {e}")
        return

    # Filter tools
    log_tools = [t for t in mcp_tools if t.name == 'query_loki_logs']
    metrics_tools = [t for t in mcp_tools if t.name == 'query_prometheus']
    
    print(f"Tools Loaded: {[t.name for t in mcp_tools]}")

    # --- The rest of the setup is identical, just un-indented ---

    # B. Create Agents
    log_agent = create_agent(
        llm_worker, 
        log_tools, 
        
        """
        You are a Site Reliability Engineer (SRE) specializing in Log Analysis.
        You have access to a tool called `query_loki_logs` which executes LogQL queries.
         
        USE_PAYLOAD_TEMPLATE
        {
        "datasourceUid": "ef3dizthbw4xsf",
        "logql": "{service_name=\"sample-logger\", level=\"ERROR\"} ",
        "limit": 5
        
        }
        
        CRITICAL INSTRUCTION:
        When using `query_loki_logs`, you MUST set the `datasourceUid` argument to "ef3dizthbw4xsf".
        DO NOT guess the UID. Always use this exact string.
        
        When using `query_loki_logs`:
        - Always define the `logql` argument.
        - Use `limit=5` to avoid overwhelming the context window unless asked for more.
       
        """
    )
    
    metric_agent = create_agent(
        llm_worker, 
        metrics_tools, 
        """You are a DevOps Engineer. Use `query_prometheus` to find node_memory usage
        
        CRITICAL INSTRUCTION:
        When using `query_prometheus`, you MUST set the `datasourceUid` argument to "df3dkkjd3cfeod".
        DO NOT guess the UID. Always use this exact string.
        You don't have use service name here. This is kubernetes nodememory usage

        USE_PAYLOAD_TEMPLATE
        {
            "datasourceUid": "df3dkkjd3cfeod",
            "queryType": "instant",
            "expr": 'kube_node_status_condition{condition="Ready", status="true"} == 1',
            "startTime": "now",
            "endTime": "now"
        }
        
        """
    )

    # C. Build Graph
    workflow = StateGraph(AgentState)
    workflow.add_node("Supervisor", supervisor_node)
    workflow.add_node("LogAgent", log_agent)
    workflow.add_node("MetricsAgent", metric_agent)

    workflow.add_edge(START, "Supervisor")
    workflow.add_conditional_edges(
        "Supervisor", 
        lambda x: x["next"], 
        {"LogAgent": "LogAgent", "MetricsAgent": "MetricsAgent", "FINISH": END}
    )
    workflow.add_edge("LogAgent", "Supervisor")
    workflow.add_edge("MetricsAgent", "Supervisor")

    app = workflow.compile()

    # D. Run (Async Stream)
    print("\n--- Starting Async SDE Agent System ---")
    user_input = "what is the reason for error in service 'sample-logger' using logs and find metrics of the kubernetes node"
    inputs = {"messages": [HumanMessage(content=user_input)]}

    async for output in app.astream(inputs):
        for key, value in output.items():
            if key == "Supervisor":
                print(f"\n[Supervisor] Next: {value['next']}")
                # Check if the supervisor has a message to print (e.g., final summary)
                if value.get("messages"):
                     print(f"Thought: {value['messages'][-1].content}")
            else:
                last_msg = value["messages"][-1]
                if isinstance(last_msg, ToolMessage):
                        # Clean output for display
                        content_preview = str(last_msg.content)[:200]
                        print(f"\n[{key}] Tool Output: {content_preview}...")
                else:
                        print(f"\n[{key}] Output: {last_msg.content}")
    
    # E. Cleanup (Optional but good practice if the client supports it later)
    # await client.close() 

# --- Run Logic ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("System stopped.")
