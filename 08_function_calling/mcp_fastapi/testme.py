# testme.py
# Build and Test a Stateless MCP Server (Python)
# Pairs with mcp_plumber/testme.R
# Tim Fraser

# What is an MCP server?
#   MCP = Model Context Protocol — a standard that lets LLMs call external tools
#   over HTTP. Instead of defining tools locally, you host them as endpoints.
#   Any MCP-compatible client (Claude Desktop, Cursor, etc.) can discover and
#   call your tools automatically.
#
# This script walks through:
#   1. What the server looks like (server.py)
#   2. How to run it locally and test it by hand
#   3. How to connect it to an LLM via the Ollama API

# Start the server before running this script:
#   uvicorn server:app --port 8000 --reload
#   (from mcp_fastapi/), or: python runme.py

# 0. SETUP ###################################
print("# 0. SETUP ###################################")

print("Note: Run this script from the mcp_fastapi/ folder.")

# 0.1 Import Libraries #################################
import requests   # for HTTP requests — pip install requests
import json
import os
import runpy     # for executing another Python script
from dotenv import load_dotenv

# 0.2 Environment Variables #################################
# Load the env file to get the CONNECT_SERVER and CONNECT_API_KEY
load_dotenv()

## 0.3 Start Ollama Server (source 01_ollama.py) #################################

# Execute 01_ollama.py as if we were sourcing it in R.
# This will configure environment variables and start `ollama serve` in the background.
# Adjust if needed.
# ollama_script_path = os.path.join(os.getcwd(), "01_ollama.py")
# _ = runpy.run_path(ollama_script_path)

# 0.4 Set the server URL #################################
# Local: set MCP_SERVER=http://127.0.0.1:8000/mcp (and run server.py / runme.py first).
# Deployed: default Connect URL; set CONNECT_API_KEY in .env for Authorization.
SERVER = os.getenv(
    "MCP_SERVER",
    "https://connect.systems-apps.com/fastapimcp/mcp",
)

# ── Helper: send one JSON-RPC request ───────────────────────

def mcp_request(method, params=None, id=1):
    body = {"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}
    headers = {}
    api_key = os.getenv("CONNECT_API_KEY")
    if api_key:
        headers["Authorization"] = f"Key {api_key}"
    resp = requests.post(SERVER, json=body, headers=headers)
    resp.raise_for_status()
    return resp.json().get("result")

# 1. HANDSHAKE — initialize ##############################
print("# 1. HANDSHAKE - initialize ##############################")

# Every MCP session begins with an initialize call.
# The server responds with its name, version, and capabilities.

init = mcp_request("initialize", {
    "protocolVersion": "2025-03-26",
    "clientInfo":      {"name": "py-test-client", "version": "0.1.0"},
    "capabilities":    {}
})

print(f"Server: {init['serverInfo']['name']} v {init['serverInfo']['version']}")

# 2. DISCOVER TOOLS — tools/list #########################
print("# 2. DISCOVER TOOLS - tools/list #########################")

# Ask the server what tools it exposes.
tools = mcp_request("tools/list")
print("Available tools:")
for t in tools["tools"]:
    print(f"  - {t['name']}: {t['description']}")

# 3. CALL A TOOL — tools/call ############################
print("# 3. CALL A TOOL - tools/call ############################")

result = mcp_request("tools/call", {
    "name":      "summarize_dataset",
    "arguments": {"dataset_name": "iris"}
})

print(result["content"][0]["text"])

# 3b. CALL SECOND TOOL DIRECTLY — linear_regression #####
print("# 3b. CALL SECOND TOOL - linear_regression (direct tools/call) ########")

result_lr = mcp_request("tools/call", {
    "name":      "linear_regression",
    "arguments": {
        "dataset_name": "mtcars",
        "x_column":     "wt",
        "y_column":     "mpg",
    },
}, id=2)

print(result_lr["content"][0]["text"])
print()


# 4. CONNECT AN LLM TO THE MCP SERVER ####################
print("# 4. CONNECT AN LLM TO THE MCP SERVER ####################")

# So far you've called the MCP server directly.
# Now let the LLM decide *when* to call it and with *what* arguments.
#
# Pattern:
#   a. Pull tool metadata from the server (tools/list)
#   b. Convert to Ollama's expected format
#   c. Pass to the chat API just like local tools
#   d. When the LLM returns a tool_call, POST it to tools/call yourself
#
# Step 4 needs Ollama listening (default http://127.0.0.1:11434). If it is not
# running, we skip 4c–4d instead of crashing with "connection refused".

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
CHAT_URL = f"{OLLAMA_BASE}/api/chat"
MODEL = "smollm2:1.7b"


def ollama_is_running():
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=2)
        return r.ok
    except requests.RequestException:
        return False


## 4a. Fetch tool metadata from the server ---------------
print("# 4a. FETCH TOOL METADATA FROM THE SERVER ####################")
tools_raw = mcp_request("tools/list")["tools"]

## 4b. Convert MCP format -> Ollama format ----------------
# MCP uses inputSchema; Ollama uses parameters — they're the same structure.
print("# 4b. CONVERT MCP FORMAT -> OLLAMA FORMAT ####################")


def mcp_to_ollama(tool):
    return {
        "type": "function",
        "function": {
            "name":        tool["name"],
            "description": tool["description"],
            "parameters":  tool["inputSchema"]
        }
    }

ollama_tools = [mcp_to_ollama(t) for t in tools_raw]


def ollama_then_mcp(user_message: str, mcp_id_start: int) -> int:
    """
    One chat with tools; execute the first tool_call via MCP; print tool name, args, and text.
    Returns next id for mcp_request (incremented once if a call was made).
    """
    messages = [{"role": "user", "content": user_message}]
    body = {"model": MODEL, "messages": messages, "tools": ollama_tools, "stream": False}
    resp = requests.post(CHAT_URL, json=body, timeout=120)
    resp.raise_for_status()
    result_llm = resp.json()

    tool_calls = result_llm.get("message", {}).get("tool_calls", [])
    if not tool_calls:
        print("No tool_calls in the model response - try another model or prompt.")
        return mcp_id_start

    tc = tool_calls[0]
    func_name = tc["function"]["name"]
    raw_args = tc["function"]["arguments"]
    # Ollama versions differ: arguments may be a JSON string or already a dict.
    func_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

    mcp_result = mcp_request(
        "tools/call",
        {"name": func_name, "arguments": func_args},
        id=mcp_id_start,
    )

    print(f"LLM chose tool: {func_name}")
    print(f"Tool arguments: {json.dumps(func_args, indent=2)}")
    print("MCP tools/call result:")
    print(mcp_result["content"][0]["text"])
    return mcp_id_start + 1


if not ollama_is_running():
    print(
        f"Skipping steps 4c-5: no Ollama API at {OLLAMA_BASE} (connection refused or timeout).\n"
        "Start Ollama, then run this script again - or set OLLAMA_HOST if Ollama runs elsewhere."
    )
else:
    ## 4c-4d. LLM + summarize_dataset -----------------------
    print("# 4c. ASK THE LLM (summarize mtcars) ####################")
    next_id = ollama_then_mcp("Give me a summary of the mtcars dataset.", mcp_id_start=10)

    ## 5. LLM + linear_regression (natural language) -------
    print()
    print("# 5. ASK THE LLM (regress mpg on weight in mtcars) ####################")
    ollama_then_mcp(
        (
            "For the mtcars dataset, how is mpg related to car weight? "
            "Use the linear regression tool with predictor wt and outcome mpg. "
            "I want slope, intercept, and R-squared."
        ),
        mcp_id_start=next_id,
    )
