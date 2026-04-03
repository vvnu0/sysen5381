# manifestme.R
# Write manifest.json for Posit Connect (Plumber API + Python deps for reticulate)
# Tim Fraser
#
# From repo root: Rscript 10_data_management/agentr/manifestme.R
# Or: cd 10_data_management/agentr && Rscript manifestme.R

args = commandArgs(trailingOnly = FALSE)
f = sub("^--file=", "", args[grepl("^--file=", args)])[1]
if (!is.na(f) && nzchar(f)) {
  setwd(dirname(normalizePath(f, winslash = "/", mustWork = FALSE)))
}

if (!requireNamespace("rsconnect", quietly = TRUE)) {
  stop("install.packages('rsconnect')")
}

here = normalizePath(getwd(), winslash = "/", mustWork = FALSE)
rsconnect::writeManifest(
  appDir = here,
  appPrimaryDoc = "plumber.R",
  appMode = "api",
  forceGeneratePythonEnvironment = TRUE
)
