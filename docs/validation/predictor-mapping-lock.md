# Predictor Mapping Lock

Date: 2026-04-28

This document locks the first-pass NHAMCS 2022 predictor support decision before empirical fitting. In plain English: the app has seven prototype inputs, but the first NHAMCS reduced fit can defend only two of them.

Status note, 2026-05-04: the active app model is now `e-dispo-v4.1-pas5-high-acuity-surrogate`, a later pooled NHAMCS 2018-2022 refit using exact age, `pain_severe`, fever/temperature proxy, vomiting, tachycardia burden, and PAS-5 `high_acuity_proxy` bridged through NHAMCS `IMMEDR` surrogate evidence. This document remains historical support for the earlier first-pass mapping.

| App predictor | NHAMCS support | Fit status | Locked decision |
|---|---|---|---|
| `ageBand` | Direct | Included | Use `AGE` grouped into 18-29, 30-44, 45-54, and 55-64. |
| `broadPainRegion` | Weak proxy | Excluded | RFV abdominal pain codes identify abdominal pain but do not reliably separate upper/lower/diffuse pain location for this first fit. |
| `painSeverity` | Direct | Included | Use `PAINSCALE` grouped into mild 0-3, moderate 4-6, and severe 7-10. Negative and missing values are excluded from the reduced fit. |
| `onsetDurationCategory` | Unavailable | Prototype only | Do not fit in NHAMCS unless a defensible source variable or proxy is later identified. |
| `constantVsIntermittent` | Unavailable | Prototype only | Do not fit in NHAMCS unless a defensible source variable or proxy is later identified. |
| `vomiting` | Proxy | Excluded | Possible symptom/RFV/diagnosis proxy, but not locked for the first reduced model. |
| `fever` | Proxy | Excluded | Possible symptom/RFV/diagnosis/temperature proxy, but not locked for the first reduced model. |

## Reduced Empirical Model

The reduced empirical candidate is:

```text
logit(P(admit)) = intercept + ageBand terms + painSeverity terms
```

`admit` still means same-hospital hospitalization/admission after endpoint-refined exclusions.

## Lay Summary

The prototype app asks seven questions because that is useful for the class demonstration. The real public dataset does not cleanly contain all seven answers. For the first data-based fit, only age and pain score are strong enough to use. The other fields stay in the app as prototype-only inputs until a better source or defensible proxy is documented.

## Promotion Rule

Do not activate NHAMCS-derived coefficients in the app unless the artifact schema passes and the reviewer accepts this reduced predictor set or approves a stronger mapping.
