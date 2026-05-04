# Validation Source Table

| Source | Why it matters | Link |
|---|---|---|
| TRIPOD+AI | Reporting checklist for prediction-model development and evaluation. | https://www.bmj.com/content/385/bmj-2023-078378 |
| PROBAST+AI | Risk-of-bias, quality, and applicability framework. | https://www.bmj.com/content/388/bmj-2024-082505 |
| FDA Clinical Decision Support Software guidance | Boundary reference for avoiding directive clinical CDS claims. | https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software |
| DECIDE-AI | Later-stage reference for early live evaluation of AI decision support. | https://www.nature.com/articles/s41591-022-01772-9 |
| CDC NHAMCS documentation index | Public-use data documentation source. | https://www.cdc.gov/nchs/nhamcs/documentation/index.html |
| 2022 NHAMCS ED public-use documentation | Codebook and variable reference for the audited file. | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/nhamcs/doc22-ed-508.pdf |
| 2022 NHAMCS ED Stata archive | Raw public-use Stata file used locally by the offline pipeline. | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/stata/ed2022-stata.zip |
| 2022 NHAMCS ED summary tables | Contextual ED visit and disposition table reference. | https://www.cdc.gov/nchs/data/nhamcs/web_tables/2022-nhamcs-ed-web-tables.pdf |
| CDC masked design variables guidance | NHAMCS public-use files include masked design variables for variance estimation with ultimate-cluster/single-stage design software. | https://archive.cdc.gov/www_cdc_gov/nchs/data/ahcd/ultimatecluster.pdf |
| 2022 NHCS ED public-use file | Open web-available ED encounter file with demographics, diagnosis codes, CCSR flags, discharge status, and survey weights; useful for cohort sizing but not sufficient for active `e-dispo-v4.1` validation because the public-use ED file lacks the strict admission endpoint and key predictor fields. | https://www.cdc.gov/nchs/nhcs/data/index.html |
| AHRQ NEDS file specifications | Future endpoint-scale validation option if access is available. | https://hcup-us.ahrq.gov/db/nation/neds/nedsfilespecs.jsp |
| MIMIC-IV-ED | Granular ED replication/proxy-validation source with approximately 425,000 BIDMC ED stays from 2011-2019 and ED tables for stays, triage, vitals, diagnoses, and medications. | https://physionet.org/content/mimic-iv-ed/2.2/ |
| NHS England Emergency Care Data Set (ECDS) | Restricted UK external-validation candidate with patient-level England ED attendance data available through DARS/SDE or approved extract; free-text clinical narrative availability is unconfirmed in the current analytical product. | https://digital.nhs.uk/services/data-access-request-service-dars/dars-products-and-services/data-set-catalogue/emergency-care-data-set-ecds |

## Reviewer Note

The standards above do not prove that the model is valid. They define what the next validation report must contain before any empirical or clinical-sounding claim is appropriate.
