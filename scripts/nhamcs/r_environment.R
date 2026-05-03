#!/usr/bin/env Rscript

# Shared R environment helpers for NHAMCS survey-weighted fitting.
#
# Do not vendor a full user R package library into the repository. This helper
# makes the survey workflow reproducible by using explicit library paths:
#   1. NHAMCS_R_LIBS, if set
#   2. R_LIBS_USER, if set
#   3. repo-local r-lib directories, if present
#   4. the user's existing OneDrive R library only when it matches active R

nhamcs_split_paths <- function(value) {
  if (is.null(value) || identical(value, "")) {
    return(character())
  }
  parts <- unlist(strsplit(value, .Platform$path.sep, fixed = TRUE), use.names = FALSE)
  parts[nzchar(parts)]
}

nhamcs_default_r_library_paths <- function() {
  env_paths <- c(
    nhamcs_split_paths(Sys.getenv("NHAMCS_R_LIBS", "")),
    nhamcs_split_paths(Sys.getenv("R_LIBS_USER", ""))
  )
  r_minor <- paste(R.version$major, strsplit(R.version$minor, ".", fixed = TRUE)[[1]][[1]], sep = ".")
  candidate_paths <- c(
    file.path(getwd(), "r-lib"),
    file.path(getwd(), "scripts", "nhamcs", "r-lib"),
    file.path("C:/Users/lawto/OneDrive/Documents/R/win-library", r_minor)
  )
  if (tolower(Sys.getenv("NHAMCS_ALLOW_LEGACY_ONEDRIVE_R_LIB", "")) %in% c("1", "true", "yes")) {
    candidate_paths <- c(candidate_paths, "C:/Users/lawto/OneDrive/Documents/R/win-library/4.1")
  }
  unique(normalizePath(c(env_paths, candidate_paths), winslash = "/", mustWork = FALSE))
}

nhamcs_configure_r_environment <- function(extra_paths = character()) {
  paths <- unique(c(extra_paths, nhamcs_default_r_library_paths()))
  existing_paths <- paths[file.exists(paths)]
  if (length(existing_paths) > 0) {
    .libPaths(unique(c(existing_paths, .libPaths())))
  }
  list(
    r_home = R.home(),
    r_version = paste(R.version$major, R.version$minor, sep = "."),
    configured_library_paths = existing_paths,
    active_library_paths = .libPaths()
  )
}

nhamcs_package_status <- function(packages) {
  rows <- lapply(packages, function(package) {
    available <- requireNamespace(package, quietly = TRUE)
    version <- ""
    if (available) {
      version <- as.character(utils::packageVersion(package))
    }
    data.frame(
      package = package,
      available = available,
      version = version,
      stringsAsFactors = FALSE
    )
  })
  do.call(rbind, rows)
}

nhamcs_write_r_environment_report <- function(output_dir, required_packages = c("survey")) {
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  package_status <- nhamcs_package_status(required_packages)
  lines <- c(
    "# NHAMCS R Environment Report",
    "",
    paste0("R home: ", R.home()),
    paste0("R version: ", paste(R.version$major, R.version$minor, sep = ".")),
    "",
    "## Active Library Paths",
    paste0("- ", .libPaths()),
    "",
    "## Required Packages",
    apply(
      package_status,
      1,
      function(row) {
        paste0("- ", row[["package"]], ": available=", row[["available"]], ", version=", row[["version"]])
      }
    ),
    "",
    "## Notes",
    "- Set NHAMCS_R_LIBS to add a repo-local or machine-local R package library path.",
    "- The existing OneDrive R library is used only when it matches the active R minor version, unless NHAMCS_ALLOW_LEGACY_ONEDRIVE_R_LIB is explicitly enabled.",
    "- Full R package libraries should not be committed to the repository."
  )
  writeLines(lines, file.path(output_dir, "r_environment_report.md"), useBytes = TRUE)
  invisible(package_status)
}
