# NHS England ECDS Procurement And Usefulness Assessment

Date: 2026-05-04

## Bottom Line

The likely target dataset is NHS England's Emergency Care Data Set (ECDS), the national urgent and emergency care data product for England. Record-level data was not procured in this work session because it is not a public download. NHS England routes ECDS access through DARS, with the NHS England Secure Data Environment (SDE) or an approved extract as access methods.

Public metadata and technical documentation were reviewed. ECDS is a high-potential external validation source for the locked `e-dispo-v4.1-pas5-high-acuity-surrogate` educational model, especially if accessed as structured ECDS plus linked HES admitted-patient-care data. It is not immediately usable until DARS access is approved and the exact field availability is confirmed.

The free-text claim needs caution. Older ECDS v2.1 implementation material includes `EmCare_Clinical_Narrative` as local free text, but the current public analytical ECDS data model reviewed here exposes structured tables and does not show that clinical narrative field. Treat national free-text availability as unconfirmed until NHS England or a regional/trust SDE confirms it in the approved DARS data-item list.

## Procurement Status

| Item | Status | Notes |
|---|---|---|
| Public metadata | Procured | NHS England ECDS product, DARS catalogue, ATOS page, data model, SDE, DARS guidance, and legacy ECDS v2.1 free-text reference were reviewed. |
| Record-level ECDS | Blocked | Requires DARS application, legal basis, security assurance, approved Data Sharing Agreement, and SDE or extract provisioning. |
| Free-text ED notes | Unconfirmed | Current analytical data model does not list `EmCare_Clinical_Narrative`; older v2.1 local-submission specification does. |
| Model validation run | Not possible yet | No approved record-level extract or SDE workspace is available in this repository. |

## Sources Reviewed

| Source | Relevant finding |
|---|---|
| https://digital.nhs.uk/services/data-access-request-service-dars/dars-products-and-services/data-set-catalogue/emergency-care-data-set-ecds | DARS catalogue identifies ECDS as A&E attendances at NHS hospitals in England, with SDE and extract access, England scope, October 2017 onward, monthly collection, and pseudonymised linking options. |
| https://digital.nhs.uk/data-and-information/data-collections-and-data-sets/data-sets/emergency-care-data-set-ecds/data-product | ECDS data product page says bespoke or standard extracts can be requested through DARS subject to appropriate use case and legal basis. |
| https://digital.nhs.uk/data-and-information/data-collections-and-data-sets/data-sets/emergency-care-data-set-ecds/data-product-fundamentals | Data product fundamentals describe patient-level data, SNOMED coding, official complete data from April 2020, daily provider submission, structured data groups, and ATOS filtering for DARS-specific availability. |
| https://digital.nhs.uk/binaries/content/assets/website-assets/data-and-information/datasets/ecds/emergency-care-data-set-ecds-v3-data-model-v1.0.pdf | Current data model lists structured attendance, patient, clinical, observations, assessments, diagnosis, findings, treatments, and referrals tables. |
| https://digital.nhs.uk/services/data-access-request-service-dars | DARS page identifies DARS as the gateway for NHS health and social care data and lists DSFC, DARS Online, approval, DSA, SDE/extract access, deletion/closure, and charges. |
| https://digital.nhs.uk/services/data-access-request-service-dars/process/data-access-request-service-dars-pre-application-checklist | Pre-application checklist requires DSFC for record-level data, security assurance, data minimisation, data-flow diagram, legal basis, research ethics/protocol where applicable, and DPA registration. |
| https://digital.nhs.uk/services/secure-data-environment-service | SDE page describes de-identified patient-level data access for approved researchers with output controls and DARS approval requirements. |
| https://www.england.nhs.uk/london/wp-content/uploads/2015/12/ecds-v2-1.pdf | Legacy ECDS v2.1 specification includes `EmCare_Clinical_Narrative` as local free-text notes; this is not proof that the current national analytical data product releases that field through DARS. |

## Recommended DARS Request Shape

Use SDE access rather than a raw extract if feasible. The model task does not need identifiable data, and SDE access reduces transfer and governance burden.

Requested purpose should stay narrow:

Validate, for educational/statistical research only, whether the existing `e-dispo-v4.1-pas5-high-acuity-surrogate` model transports to English emergency care data for adult men ages 18-64 presenting with non-traumatic abdominal pain. Outputs should be aggregate validation tables, calibration/discrimination summaries, missingness tables, subgroup summaries with disclosure control, and a protocol report. The data should not be used for clinical decision support, triage, treatment, discharge advice, individual patient action, direct marketing, or record-level third-party sharing.

Minimum data request:

| Field group | Needed fields |
|---|---|
| Linkage and design | Record identifier, pseudonymised person ID if available, provider/site, financial year, extract date/version. |
| Cohort | Age at arrival, stated gender, department type, attendance category/source/mode, planned arrival, chief complaint code, diagnosis codes, injury flags/codes, activity type. |
| Timings | Arrival, assessment, seen, conclusion, decision-to-admit, clinically-ready-to-proceed, departure timestamps. |
| Endpoint | Discharge status, discharge destination, follow-up, receiving site, treatment function, referred-to-service, decision-to-admit indicators/timestamps, and HES APC linkage to confirm same-hospital admission where possible. |
| Predictors | Assessment tool/person score for pain if available, clinical observations code/value/unit/timestamp for temperature and pulse/heart rate, findings/chief complaint/diagnosis codes for fever and vomiting. |
| Fairness and transport | Ethnicity, geography/region at non-disclosive level, deprivation if available, provider/site type, year/month. |
| Free text | Ask DARS explicitly whether clinical narrative or discharge text exists in the releasable analytical product. If available, request only pre-disposition, timestamped, minimised text needed for phenotype validation, with an NLP/de-identification protocol. |

## Usefulness For `e-dispo-v4.1`

| Model requirement | Expected ECDS support | Usefulness |
|---|---|---|
| Adult men ages 18-64 | Direct age and gender fields are present in the analytical model. | High. |
| Non-traumatic abdominal pain cohort | Chief complaint, diagnosis, injury-related flags, and injury mechanism/place fields can support a SNOMED-based abdominal-pain and trauma-exclusion code list. | Medium/high, pending code-list audit. |
| Same-hospital admission vs routine ED discharge home | ECDS has discharge status, destination, decision-to-admit timing, receiving site, and referral/service fields. HES APC linkage would make endpoint adjudication stronger. | High, if same-hospital admission and transfer/other exclusions can be cleanly distinguished. |
| Exact age | Direct. | High. |
| Severe pain | Current data model includes assessment records with tool code and person score, but pain-score availability and coding must be confirmed in ATOS/DARS fields. | Medium. Strong if pain scale is consistently populated; otherwise limited. |
| Fever or temperature proxy | Observation code/value/unit/timestamp fields should support objective temperature mapping. Fever symptoms may also appear in findings/chief complaint/diagnosis. | High for temperature, medium for symptom fever. |
| Vomiting | Possible through SNOMED chief complaint, finding, diagnosis, or possibly text if approved. Completeness is uncertain. | Medium. |
| Tachycardia burden | Observation code/value/unit/timestamp should support pulse/heart-rate extraction, potentially with repeated vitals. | High if HR/pulse observations are populated. |
| Calibration and discrimination | Large patient-level external dataset should support AUROC, Brier score, calibration-in-the-large, calibration slope, grouped calibration, and subgroup checks. | High after mapping lock. |
| Free-text validation | Could help symptom phenotyping if genuinely available, but may contain outcome leakage and identifying content. | Low until availability and governance are confirmed; use cautiously. |

## Validation Protocol Requirements

Before any ECDS result can affect model claims or labels, the project must produce all evidence required by the repository evidence rule:

1. Analytic cohort definition.
2. Endpoint recoding.
3. Predictor mapping.
4. Unweighted and available weighted/count summaries.
5. Cell and event counts.
6. Missingness by endpoint.
7. Fitted or transported coefficient handling.
8. Standard errors, covariance, bootstrap draws, or posterior draws as applicable.
9. Calibration diagnostics.

For an external validation first pass, do not refit coefficients. Apply the locked NHAMCS `e-dispo-v4.1` coefficients to ECDS-mapped predictors, then report transport calibration and performance. If recalibration or refitting is later performed, label it as a separate ECDS-derived model and do not overwrite `e-dispo-v4.1-pas5-high-acuity-surrogate` without a new evidence gate.

Avoid leakage:

- Use only observations and text timestamped before the modeled disposition decision.
- Do not use diagnosis, treatment, referral, discharge instructions, or narrative content that was created after disposition as predictors.
- Treat discharge status/destination and HES APC linkage as endpoint material only.
- Keep free-text NLP outputs separate from the active structured model unless explicitly validated.

## Assessment Verdict

ECDS is worth pursuing as the strongest UK external validation candidate identified so far, but only for a DARS-backed project. It should be prioritized over a generic free-text procurement strategy because the structured national data can validate the existing endpoint and most active predictors with less leakage risk.

The immediate next action is not model fitting. It is a DARS/SDE enquiry asking whether the requested structured ECDS fields and any clinical narrative fields are releasable for this narrow educational/statistical validation purpose. Until that access is approved, ECDS should remain a restricted future-validation candidate and must not be described as procured record-level data.
