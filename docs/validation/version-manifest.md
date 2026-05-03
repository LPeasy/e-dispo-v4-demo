# v3.1 Validation Baseline Manifest

Date: 2026-04-28

Status note, 2026-05-01: this file records the earlier v3.1 NHAMCS 2022 baseline. The current active educational app model is the pooled NHAMCS 2018-2022 reduced export `e-dispo-v4.0`, documented in `performance-report.md` and `predictive-power-usability-review.md`. The prior v2 export `pooled_empirical_v2_age_pain_fever_vomiting_tachycardia` remains archived in `src/data/pooledEmpiricalModel.ts`.

## Baseline Identity

- Baseline name: `v3.1-validation-baseline`.
- Endpoint spec version: `endpoint_refined_v3_2026-04-28`.
- Active app coefficient status: `prototype_assumption`.
- Empirical activation status: blocked. The generated NHAMCS reduced fit is a review artifact, not the active app model.
- Git commit: not available. The workspace is not currently anchored to a committed revision, so this manifest records file and artifact hashes instead.

## Endpoint Source

- Source package: `C:\Users\lawto\Downloads\ed_endpoint_refinement_package.zip`.
- Source package SHA-256: `88687D5A58A750DB37219DA0AC1FD6B1E7C130E20B2136809563FBA5F9E33908`.

## Validation Configuration

- Config file: `scripts/nhamcs/config.example.json`.
- Config SHA-256: `BCC9B48D6B18C7D8B407C5274D9F9A913B39ED863E4EDDD9CFB0752A541AB827`.
- Primary source dataset: 2022 NHAMCS ED public-use file.
- Local raw-data location: `data/raw/nhamcs_2022/`.
- Raw-data rule: do not commit or package raw NHAMCS files.

## Generated Artifacts

- Endpoint audit JSON: `artifacts/nhamcs/endpoint-audit-2022.json`.
- Endpoint audit SHA-256: `20F2520A0502BAA9A91CD319006BD9221D642C1B6229437DC34A0029E2829ED6`.
- Model fit JSON: `artifacts/nhamcs/model-fit-2022.json`.
- Model fit SHA-256: `87E6899DC99D908E796E1647E984FB65F1D6BD09297E2A5ADBC43BD0F88862FD`.
- CSV summaries: `artifacts/nhamcs/endpoint-audit-2022.csv` and `artifacts/nhamcs/model-fit-2022-coefficients.csv`.

## Cohort Snapshot

- All NHAMCS ED records: 16,025.
- Male records: 8,465.
- Male age 18-64: 5,066.
- Abdominal pain RFV proxy: 840.
- Strict non-trauma proxy: 721.
- Primary binary endpoint records: 660 before missing predictor exclusions.
- Reduced fit sample after pain-scale availability: 469.

## Primary Endpoint Snapshot

- Primary admit: 87 records, weighted count 855,661.188.
- Primary treat_and_release: 573 records, weighted count 5,599,557.5.
- Primary excluded: 61 records, weighted count 490,441.344.
- Exclusion categories: observation -> discharged, transfer, sentinel death, nonroutine exit, other/unknown, and conflict.

## Known Limitations

- In this historical v3.1 baseline, app coefficients remained prototype assumptions; the current app has since activated the reduced pooled empirical `e-dispo-v4.0` export for educational use.
- The reduced NHAMCS fit includes only `ageBand` and `painSeverity`.
- Onset/duration and constant/intermittent pattern are unavailable in the current NHAMCS mapping.
- Broad pain region, vomiting, and fever are not included in the reduced fit because their support is weak or proxy-dependent.
- Weighted counts use `PATWT`, but full survey-design variance is not yet implemented.
- No external validation has been performed.
- No clinical validity, diagnosis, triage, treatment, discharge-safety, or medical-advice claim is made.
