#!/usr/bin/env Rscript

script_file <- grep("^--file=", commandArgs(FALSE), value = TRUE)
script_dir <- getwd()
if (length(script_file) > 0) {
  script_dir <- dirname(normalizePath(sub("^--file=", "", script_file[[1]]), winslash = "/"))
}

source(file.path(script_dir, "r_environment.R"))

args <- commandArgs(trailingOnly = TRUE)
output_dir <- if (length(args) >= 1) args[[1]] else file.path(getwd(), "outputs", "nhamcs")

status <- nhamcs_configure_r_environment()
package_status <- nhamcs_write_r_environment_report(output_dir, required_packages = c("survey"))

cat("R_HOME=", status$r_home, "\n", sep = "")
cat("R_VERSION=", status$r_version, "\n", sep = "")
cat("CONFIGURED_LIBRARY_PATHS=", paste(status$configured_library_paths, collapse = ";"), "\n", sep = "")
cat("SURVEY_AVAILABLE=", any(package_status$package == "survey" & package_status$available), "\n", sep = "")

if (!any(package_status$package == "survey" & package_status$available)) {
  quit(status = 2)
}

quit(status = 0)
