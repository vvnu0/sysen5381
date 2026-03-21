![Banner Image](../../docs/images/icons.png)

# README `08_function_calling/mcp_server/`

> Take function calling one step further: host your tools as a live HTTP server using the **Model Context Protocol (MCP)**. Any LLM client — local or cloud — can discover and call your tools automatically.

---

## What is an MCP Server?

When you define tools locally (as you did in scripts 02–04), the tool code runs in the same process as your agent. An MCP server moves that code behind an HTTP endpoint. The LLM still decides *when* and *how* to call the tool — but now the tool lives somewhere else: a server, a colleague's machine, or a cloud deployment.

**Stateless HTTP transport** means every request is independent. No sessions, no persistent connection. Just `POST /mcp` with a JSON-RPC body.

---

## Files

| File | Language | Purpose |
|------|----------|---------|
| [`plumber.R`](plumber.R) | R | The MCP server — defines tools and handles JSON-RPC |
| [`server.py`](server.py) | Python | Same server, same tools, same protocol — in FastAPI |
| [`05_mcp_server.R`](05_mcp_server.R) | R | Test the server + connect an LLM to it |
| [`05_mcp_server.py`](05_mcp_server.py) | Python | Same, Python version |
| [`06_deploy_mcp.R`](06_deploy_mcp.R) | R | Deploy to Posit Connect via `rsconnect` |
| [`06_deploy_mcp.py`](06_deploy_mcp.py) | Python | Deploy to Posit Connect or DigitalOcean |
| [`requirements.txt`](requirements.txt) | — | Python dependencies for deployment |

---

## Quickstart

**R:**
```r
# Terminal 1 — start server
Rscript -e "plumber::plumb('plumber.R')$run(port=8000)"

# Terminal 2 — test it
source("05_mcp_server.R")
```

**Python:**
```bash
# Terminal 1 — start server
uvicorn server:app --port 8000 --reload

# Terminal 2 — test it
python 05_mcp_server.py
```

---

## Activities

- [ACTIVITY: Build and Deploy an MCP Server](ACTIVITY_mcp_server.md)

---

## Tradeoffs: Plumber vs FastAPI

Both files do identical things. The choice comes down to your stack:

| | Plumber (R) | FastAPI (Python) |
|---|---|---|
| **Deployment** | `rsconnect::deployAPI()` | `rsconnect deploy fastapi` or Docker |
| **Tool logic** | tidyverse, any R package | pandas, any Python package |
| **Performance** | Adequate for data tools | Faster for high-concurrency |
| **Client** | Posit Connect native | Connect or any cloud |

If your team lives in R, use Plumber. If you need Docker/DigitalOcean flexibility, use FastAPI.

---

![Footer Image](../../docs/images/icons.png)

← 🏠 [Back to `08_function_calling`](../README.md)
