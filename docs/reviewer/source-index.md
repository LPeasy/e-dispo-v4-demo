# Source Index For Reviewer

This file lists the main sources and project documents bundled for review.

## Project Documents

- `README.md`: main app overview, local commands, model method, and source links.
- `docs/model-card.md`: intended use, population, endpoint, predictors, analysis, data-ready path, and limitations.
- `docs/endpoint-refinement-decision-log.md`: endpoint recoding decision log.
- `docs/nhamcs-pipeline.md`: offline data pipeline and derived artifact requirements.
- `docs/class-deliverable-package.md`: class submission work-product map.
- `docs/reviewer/model-review-report.md`: plain-English model review report.
- `docs/reviewer/model-reviewer-checklist.md`: checklist for reviewer feedback.

## External Sources

- TRIPOD+AI statement: https://www.bmj.com/content/385/bmj-2023-078378
- PROBAST+AI: https://www.bmj.com/content/388/bmj-2024-082505
- CDC NHAMCS documentation: https://www.cdc.gov/nchs/nhamcs/documentation/index.html
- 2022 NHAMCS ED public-use documentation: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/dataset_documentation/nhamcs/doc22-ed-508.pdf
- 2022 NHAMCS ED summary tables: https://www.cdc.gov/nchs/data/nhamcs/web_tables/2022-nhamcs-ed-web-tables.pdf
- 2022 NHAMCS ED patient record form: https://www.cdc.gov/nchs/data/nhamcs/2022-nhamcs-ed-prf-sample-card-508.pdf
- 2022 NHAMCS ED public-use data: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NHAMCS/ed2022.zip
- 2022 NHAMCS ED Stata files: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHAMCS/stata/ed2022-stata.zip
- AHRQ NEDS file specifications: https://hcup-us.ahrq.gov/db/nation/neds/nedsfilespecs.jsp
- AHRQ NEDS EDevent note: https://hcup-us.ahrq.gov/db/vars/edevent/nedsnote.jsp
- MIMIC-IV-ED: https://physionet.org/content/mimic-iv-ed/2.2/
- FDA multiple endpoints guidance: https://www.fda.gov/media/162416/download
- Latin Hypercube uncertainty analysis overview: https://www.sciencedirect.com/science/article/abs/pii/S0951832003000589

## What These Sources Support

- NHAMCS sources support the ED public-use data path and disposition categories.
- NEDS sources support the distinction between treated/released, same-hospital admission, transfer, death, and unknown destination.
- MIMIC-IV-ED supports richer ED workflow prototyping, but not national representativeness.
- TRIPOD+AI and PROBAST+AI support transparent prediction-model reporting and bias/applicability review.
- FDA endpoint guidance supports caution about composite endpoints and component interpretation.

