# PAS-5 Acuity Candidate Screen

PAS-5 is a five-question patient-perceived acuity proxy. It is active in `e-dispo-v4.1-pas5-high-acuity-surrogate` only through the binary `high_acuity_proxy` term.

NHAMCS does not contain PAS-5 patient self-assessment answers. The candidate screen therefore maps NHAMCS `IMMEDR` 1-5 to A1-A5 only as a clinician-acuity surrogate:

| Source | Class | Binary bridge |
|---|---|---|
| `IMMEDR = 1` | A1 | `high_acuity_proxy = 1` |
| `IMMEDR = 2` | A2 | `high_acuity_proxy = 1` |
| `IMMEDR = 3` | A3 | `high_acuity_proxy = 0` |
| `IMMEDR = 4` | A4 | `high_acuity_proxy = 0` |
| `IMMEDR = 5` | A5 | `high_acuity_proxy = 0` |

`IMMEDR` values `0`, `7`, `-8`, `-9`, and missing are excluded from the primary candidate screen and reported in missingness artifacts.

The active model ID is `e-dispo-v4.1-pas5-high-acuity-surrogate`. Its formula is:

```text
admit ~ age_centered + pain_severe + fever_or_temp + vomiting_present + tachycardia_burden + high_acuity_proxy
```

`A1/A2` activate `high_acuity_proxy`; `A3/A4/A5` are the reference side.

The deterministic 2026-05-04 rerun passed the prespecified surrogate screen: binary-cell adequacy, high-acuity coefficient direction probability, leave-one-year-out AUROC gain, leave-one-year-out Brier non-worsening, apparent calibration gap, calibration slope, and complete artifact export.

Key active-screen facts:

- PAS-5/IMMEDR complete-case N: 2,245
- Admission events: 254
- High-acuity proxy coefficient: 1.24984421126593 (SE 0.315343146380296; OR 3.48979924370436)
- Apparent AUROC/Brier: 0.759077823237526 / 0.091311819980443
- Same-subset base refit AUROC/Brier: 0.736367002137274 / 0.093767198895187
- Mean leave-one-year-out AUROC gain: +0.0195420688224538
- Mean leave-one-year-out Brier change: -0.00224960097683449
- Caveat: the mean gate passed, but 2018 heldout worsened.

Conceptual context only:

- CDC/NCHS NHAMCS 2022 public-use documentation for `IMMEDR`: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/NHAMCS/doc22-ed-508.pdf
- AHRQ ESI overview: https://www.ahrq.gov/patient-safety/settings/hospital/resource/about.html
- ENA ESI handbook summary: https://enau.ena.org/AssetListing/Emergency-Severity-Index-Handbook-5th-Edition-85744/Emergency-Severity-Index-Handbook-5th-Edition-15946

These references do not validate PAS-5 as a triage tool and do not support clinical use.
