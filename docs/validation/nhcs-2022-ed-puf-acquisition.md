# NHCS 2022 ED Public-Use File Acquisition Note

Acquisition date: May 4, 2026

Source: CDC National Hospital Care Survey (NHCS) public-use data files and documentation page, updated May 1, 2026.

## Local Files

Raw files were downloaded under `e-dispo-prototype/data/raw/nhcs_2022/`. This path is ignored by `e-dispo-prototype/.gitignore`.

| File | Bytes | SHA-256 |
|---|---:|---|
| `2022-NHCS-PUF-ED-CODEBOOK.pdf` | 519,758 | `0579102FDDC4CBCBC3A258175746778A0508BA33210FE46DE7AD1FCDB2DB809B` |
| `2022-NHCS-Tech-Doc.pdf` | 738,623 | `38A93BCD5860E6F7604F05B2624A2CB82D57C5A8DA9C2EC9EC69BA62C41C11BC` |
| `nhcs2022ed_stata.do` | 20,753 | `9621EBFE2341F4C55AE505B697EB5136B05365D981EA1CF08371AC8138F7D4E1` |
| `nhcs2022ed_stata.dta` | 480,947,762 | `94C456DAEDB28FBC876071E17D2514D5CCD8D419917114E5159E36A87D830F79` |

## Initial Inventory

The ED codebook reports `497,769` records. A local read of the Stata file reproduced this count.

Key available fields:

| Domain | NHCS ED PUF support |
|---|---|
| Demographics | `age`, `sex`, `newborn` |
| Disposition-like field | `DISCHARGE_STATUS` with values for routine home, AMA, transfers, home health, hospice, other, dead, and missing |
| Diagnoses | `DX1` through `DX30`, truncated ICD-10-CM codes |
| Abdominal-pain proxy | `CCSR_SYM006`, abdominal pain and other digestive/abdomen signs and symptoms |
| Nausea/vomiting proxy | `CCSR_SYM004`, nausea and vomiting |
| Survey weights | `PUF_ENCWGT_BASE` plus 100 replicate weights |

Key missing fields for `e-dispo-v4.0` validation:

| Active model need | Status in NHCS 2022 ED PUF |
|---|---|
| Strict same-hospital inpatient admission vs routine ED discharge home endpoint | Not directly available in the public-use ED file |
| Pain severity | Not available |
| Fever or temperature | Not available |
| Vomiting as presenting symptom | Not directly available; only diagnosis-based `CCSR_SYM004` proxy |
| Tachycardia or heart rate burden | Not available |
| Chief complaint or free-text note | Not available |

## First-Pass Counts

Unweighted and base-weighted counts from local read:

| Cohort slice | Unweighted records | Base-weight sum |
|---|---:|---:|
| All ED PUF records | 497,769 | 128,909,418.29 |
| Male, age 18-64, not newborn | 130,800 | 34,172,805.79 |
| Male, age 18-64, not newborn, `CCSR_SYM006 = 1` | 12,348 | 3,128,470.04 |
| Male, age 18-64, not newborn, `CCSR_SYM006 = 1`, `CCSR_SYM004 = 1` | 3,188 | 820,915.68 |

`DISCHARGE_STATUS` distribution for the adult male abdominal-pain proxy slice:

| Value | Label | Records |
|---:|---|---:|
| -9 | Missing | 857 |
| 1 | Routine to home | 10,291 |
| 2 | Left against medical advice | 743 |
| 3 | Transfer to short-term facility | 101 |
| 4 | Transfer to long-term facility | 23 |
| 5 | Home health care | 80 |
| 6 | Hospice care - home or medical facility | 12 |
| 7 | Other | 214 |
| 8 | Dead | 27 |

## Usefulness Verdict

NHCS 2022 ED PUF is useful as an open, web-available external data source for broad feasibility checks, diagnosis-code cohort sizing, weighted descriptive comparisons, and limited discharge-status sensitivity work.

It is not sufficient to validate the active `e-dispo-v4.0` model as specified because the public-use ED file does not expose the strict same-hospital inpatient admission endpoint or the key predictor fields for pain severity, fever/temperature, vomiting as a presenting symptom, or tachycardia burden.

No NHCS-derived coefficient, prior, app parameter, or empirical label should be promoted from this acquisition note. A future NHCS pipeline should remain explicitly `unsupported` or `prototype_assumption` unless the endpoint, predictor mapping, missingness, fitted model, uncertainty, and calibration requirements in the repository evidence label rule are satisfied.

## Source URLs

- CDC NHCS data page: https://www.cdc.gov/nchs/nhcs/data/index.html
- 2022 ED codebook: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHCS/2022/2022-NHCS-PUF-ED-CODEBOOK.pdf
- 2022 technical documentation: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHCS/2022/2022-NHCS-Tech-Doc.pdf
- 2022 ED Stata data file: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHCS/2022/nhcs2022ed_stata.dta
- 2022 ED Stata input statements: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHCS/2022/nhcs2022ed_stata.do
