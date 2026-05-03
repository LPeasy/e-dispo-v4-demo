-- MIMIC-IV-ED extraction skeleton for the ED disposition replication workflow.
-- Adjust project, schema, and table names for BigQuery or Postgres.

-- edstays.csv
SELECT
  subject_id,
  hadm_id,
  stay_id,
  intime,
  outtime,
  gender,
  race,
  arrival_transport,
  disposition
FROM mimiciv_ed.edstays;

-- triage.csv
SELECT
  subject_id,
  stay_id,
  temperature,
  heartrate,
  resprate,
  o2sat,
  sbp,
  dbp,
  pain,
  acuity,
  chiefcomplaint
FROM mimiciv_ed.triage;

-- diagnosis.csv
SELECT
  subject_id,
  stay_id,
  seq_num,
  icd_code,
  icd_version,
  icd_title
FROM mimiciv_ed.diagnosis;

-- Optional age_at_ed.csv when MIMIC-IV core tables are available.
-- This approximation follows the anchor_age/anchor_year convention and should
-- be reviewed before non-exploratory use.
SELECT
  e.subject_id,
  e.stay_id,
  p.gender,
  p.anchor_age + EXTRACT(YEAR FROM e.intime) - p.anchor_year AS age_at_ed
FROM mimiciv_ed.edstays e
JOIN mimiciv_hosp.patients p
  ON e.subject_id = p.subject_id;
