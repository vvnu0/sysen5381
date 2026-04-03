# runme.R
# Run the Plumber agent API locally (port 8000)
# Tim Fraser

args = commandArgs(trailingOnly = FALSE)
f = sub("^--file=", "", args[grepl("^--file=", args)])[1]
if (!is.na(f) && nzchar(f)) {
  root = normalizePath(dirname(f), winslash = "/", mustWork = FALSE)
  setwd(root)
}
Sys.setenv(AGENTR_ROOT = normalizePath(getwd(), winslash = "/", mustWork = FALSE))
if (file.exists(".env")) {
  readRenviron(".env")
}

plumber::plumb("plumber.R")$run(host = "0.0.0.0", port = 8000L)
