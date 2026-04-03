# deployme.R
# Deploy plumber.R to Posit Connect (R API + requirements.txt for reticulate)
# Tim Fraser
#
# Prerequisites: .env with CONNECT_SERVER and CONNECT_API_KEY (see .env.example).
# On Connect, set OLLAMA_API_KEY, OLLAMA_HOST, OLLAMA_MODEL, optional SERPER_API_KEY.
#
# Run from the agentr/ folder: Rscript deployme.R

args = commandArgs(trailingOnly = FALSE)
f = sub("^--file=", "", args[grepl("^--file=", args)])[1]
if (!is.na(f) && nzchar(f)) {
  setwd(dirname(normalizePath(f, winslash = "/", mustWork = FALSE)))
}

library(rsconnect)

if (file.exists(".env")) {
  readRenviron(".env")
}

server_url = Sys.getenv("CONNECT_SERVER", unset = "")
api_key = Sys.getenv("CONNECT_API_KEY", unset = "")
if (!nzchar(server_url) || !nzchar(api_key)) {
  stop("Set CONNECT_SERVER and CONNECT_API_KEY in .env")
}

rsconnect::addServer(url = server_url, name = "posit_connect")

app_name = Sys.getenv("CONNECT_TITLE", unset = "course-autonomous-agent-r")

rsconnect::deployAPI(
  api = normalizePath(getwd(), winslash = "/", mustWork = FALSE),
  server = "posit_connect",
  appName = app_name,
  forceUpdate = TRUE
)
