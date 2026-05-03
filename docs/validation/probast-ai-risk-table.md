# PROBAST+AI-Style Risk Table

This is a practical class-project risk table, not a formal PROBAST+AI rating.

| Domain | Current concern | Current risk | Required next action |
|---|---|---|---|
| Participants | Cohort is narrow by design: adult men ages 18-64 with non-traumatic abdominal pain. | Medium | Report cohort flow, weighted counts, and subgroup availability before any generalization. |
| Predictors | `e-dispo-v4.0` uses exact age, severe pain status, fever/temperature proxy, vomiting, and tachycardia burden; other worksheet inputs remain excluded. | High | Keep excluded predictors separate or define defensible proxies before fitting them. |
| Outcome | Endpoint recoding is explicit but depends on correct flag interpretation. | Medium | Reviewer must verify 2022 NHAMCS variable names and code meanings against the codebook. |
| Analysis | Reduced fit is generated but not survey-design complete. | High | Add design-aware variance, missingness tables, intervals, and calibration plots. |
| Performance | Apparent and lightweight bootstrap summaries are available. | Medium/high | Add stronger internal validation and, if possible, external validation. |
| Applicability | App remains educational and is not intended for patient care. | High for clinical use | Maintain non-clinical language and do not deploy as CDS. |
| Fairness | Adult men only, but subgroup performance is not yet reported. | Medium/high | Add age-band, race/ethnicity, payer, region, and proxy-availability analyses. |

## Lay Summary

The biggest issue is not the web app. The biggest issue is whether the data can support the questions the app asks. The active empirical fit uses a smaller evidence-gated predictor set than the full worksheet. The next phase must either improve data mapping or keep accepting a smaller active model.
