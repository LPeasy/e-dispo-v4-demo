# PAS-5 Acuity Candidate Screen

PAS-5 is a five-question patient-perceived acuity proxy. It is collected in the app for education and review, but it does not affect `e-dispo-v4.0` P(admit).

NHAMCS does not contain PAS-5 patient self-assessment answers. The candidate screen therefore maps NHAMCS `IMMEDR` 1-5 to A1-A5 only as a clinician-acuity surrogate:

| Source | Class | Binary bridge |
|---|---|---|
| `IMMEDR = 1` | A1 | `high_acuity_proxy = 1` |
| `IMMEDR = 2` | A2 | `high_acuity_proxy = 1` |
| `IMMEDR = 3` | A3 | `high_acuity_proxy = 0` |
| `IMMEDR = 4` | A4 | `high_acuity_proxy = 0` |
| `IMMEDR = 5` | A5 | `high_acuity_proxy = 0` |

`IMMEDR` values `0`, `7`, `-8`, `-9`, and missing are excluded from the primary candidate screen and reported in missingness artifacts.

The candidate model ID is `e-dispo-v4.1-pas5-high-acuity-surrogate`. If activated after separate review, its formula is:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + high_acuity_proxy
```

`A1/A2` activate `high_acuity_proxy`; `A3/A4/A5` are the reference side.

Activation requires all gates in `scripts/nhamcs/nhamcs_pas5_acuity_candidate_screen.R` to pass: binary-cell adequacy, high-acuity coefficient direction probability, leave-one-year-out AUROC gain, leave-one-year-out Brier non-worsening, apparent calibration gap, calibration slope, and complete artifact export.

Conceptual context only:

- CDC/NCHS NHAMCS 2022 public-use documentation for `IMMEDR`: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/NHAMCS/doc22-ed-508.pdf
- AHRQ ESI overview: https://www.ahrq.gov/patient-safety/settings/hospital/resource/about.html
- ENA ESI handbook summary: https://enau.ena.org/AssetListing/Emergency-Severity-Index-Handbook-5th-Edition-85744/Emergency-Severity-Index-Handbook-5th-Edition-15946

These references do not validate PAS-5 as a triage tool and do not support clinical use.
