# NHAMCS 2022 Offline Pipeline

This script is the reproducible path from CDC public-use data to a small derived artifact for the web app. It should be run outside the static app bundle.

## Commands

Download and extract the CDC 2022 NHAMCS ED Stata archive:

```powershell
python scripts/nhamcs/derive_nhamcs_2022.py --config scripts/nhamcs/config.example.json --download
```

Use an already-downloaded Stata file:

```powershell
python scripts/nhamcs/derive_nhamcs_2022.py --config scripts/nhamcs/config.example.json --raw-dir data/raw/nhamcs_2022
```

Attempt logistic coefficient fitting:

```powershell
python scripts/nhamcs/derive_nhamcs_2022.py --config scripts/nhamcs/config.example.json --raw-dir data/raw/nhamcs_2022 --fit
```

Generate the v3.1 validation artifacts and reports:

```powershell
python scripts/nhamcs/validate_nhamcs_2022.py
```

Run the endpoint fixture test:

```powershell
python scripts/nhamcs/test_validate_nhamcs_2022.py
```

If the system Python lacks `pandas`, run the same commands with the bundled workspace Python runtime.

## R Survey-Weighted Fitting Environment

The folder `C:\Users\lawto\OneDrive\Documents\R` is a user package library, not an R runtime. It should not be copied wholesale into this repository. The repo now includes a small R environment shim that makes the survey workflow use explicit library paths when R is installed:

1. `NHAMCS_R_LIBS`, if set.
2. `R_LIBS_USER`, if set.
3. `r-lib/` or `scripts/nhamcs/r-lib/`, if present locally.
4. `C:/Users/lawto/OneDrive/Documents/R/win-library/<active R minor version>`, if present on this machine.

Install and verify R outside git:

```powershell
winget install --id RProject.R -e
Rscript --version
Rscript -e "install.packages('survey', repos='https://cloud.r-project.org')"
```

Check the R environment:

```powershell
Rscript scripts/nhamcs/check_r_environment.R outputs/nhamcs
```

Run the survey-weighted candidate fit:

```powershell
Rscript scripts/nhamcs/nhamcs_survey_fit.R outputs/nhamcs/analytic_cohort_nhamcs.csv outputs/nhamcs
```

Run the integrated NHAMCS pipeline:

```powershell
python scripts/nhamcs/run_nhamcs_pipeline.py --survey-mode auto
python scripts/nhamcs/run_nhamcs_pipeline.py --survey-mode require
python scripts/nhamcs/run_nhamcs_pipeline.py --survey-mode off
```

If `Rscript` is not on PATH, set `RSCRIPT_PATH` for the Python environment or pass `--rscript C:\full\path\to\Rscript.exe`. If `survey` is absent, install it into one of the configured library paths or set `NHAMCS_R_LIBS` to the library containing it. `auto` writes exploratory Python outputs plus a blocker when R is unavailable; `require` fails loudly; `off` keeps only the exploratory fallback. Survey-weighted outputs remain `survey_weighted_candidate` until all evidence gates pass.

## Pooled NHAMCS 2018-2022 Workflow

The pooled workflow is parallel to the 2022-only workflow. It does not replace or promote the active app model.

Expected raw-file layout:

```powershell
data/nhamcs/2018/
data/nhamcs/2019/
data/nhamcs/2020/
data/nhamcs/2021/
data/nhamcs/2022/
```

Build yearly cohorts first, then append and fit:

```powershell
python scripts/nhamcs/build_yearly_cohorts.py --years 2018 2019 2020 2021 2022
python scripts/nhamcs/build_pooled_cohort.py --years 2018 2019 2020 2021 2022
python scripts/nhamcs/run_nhamcs_pooled_pipeline.py --years 2018 2019 2020 2021 2022 --survey-mode auto
```

Require R survey fitting:

```powershell
Rscript scripts/nhamcs/check_r_environment.R outputs/nhamcs_pooled
python scripts/nhamcs/run_nhamcs_pooled_pipeline.py --years 2018 2019 2020 2021 2022 --survey-mode require
```

The pooled cohort writes `pooled_weight = PATWT / number_of_years`, `pooled_stratum = interaction(year, CSTRATM)`, and `pooled_psu = interaction(year, CPSUM)`. Outputs remain `survey_weighted_candidate` or exploratory until codebook mapping, missingness, uncertainty, calibration, sensitivity, and evidence gates are reviewed. The pooled pipeline writes a blocker report instead of fabricating results when annual files are missing.

## Review Requirements

The example config now contains the endpoint-refined v3.1 baseline mapping, but it still requires review before app activation:

1. Verify variable names and code values against the official 2022 NHAMCS ED documentation.
2. Review the abdominal pain RFV rule and non-trauma proxy rule.
3. Review refined disposition flag mappings for `ADMITHOS`, `OBSHOS`, `OBSDIS`, `NOFU`, `RETRNED`, `RETREFFU`, transfer flags, death flags, nonroutine exits, other/unknown flags, and row-level conflicts.
4. Confirm which predictors are direct, proxy-only, or unavailable.
5. Confirm the artifact reports primary endpoint counts, Sensitivity A/B counts, exclusion counts, and conflict counts.
6. Confirm calibration, discrimination, missingness, internal validation, and sensitivity analyses.
7. Validate the output with `validateCoefficientArtifact` before copying it into app data.

If the output has no empirical coefficients, no calibration result, or no reviewed refined endpoint cohort, the app must continue to show prototype assumption labels.
