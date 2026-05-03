# Current Model Glossary

This glossary explains the main technical words used in the review package.

## Logistic Regression

A model that turns several inputs into a probability between 0 and 1.

In this app, logistic regression estimates `P(admit)`, the model probability of same-hospital admission for the selected input profile.

## Coefficient

A number that tells the model how much one input changes the estimate.

A positive coefficient pushes `P(admit)` upward. A negative coefficient pushes it downward.

## Odds Ratio

A way to describe how odds change when one input changes.

An odds ratio above 1 means the odds go up. An odds ratio below 1 means the odds go down. Odds are not the same as probability, so this package mostly uses probabilities in the main explanation.

## Calibration

How closely predicted probabilities match observed outcomes.

If a model says "about 10%" for many similar cases, good calibration would mean about 10% of those cases actually had the event in the source data.

## AUROC

A ranking score.

AUROC asks whether the model tends to rank admitted visits higher than released visits. A value of 0.5 is no better than chance. A value of 1.0 is perfect ranking. The current model's AUROC is 0.713, which is moderate.

## Brier Score

A probability-error score.

Lower is better. The current model's Brier score is 0.0977. The improvement over a simple prevalence-only baseline is small, so the package describes predictive power as limited.

## NHAMCS

The National Hospital Ambulatory Medical Care Survey.

It is a public CDC/NCHS survey source for ambulatory and emergency department care. This project uses pooled NHAMCS 2018-2022 evidence for the active educational model.

## Endpoint

The outcome the model is trying to estimate.

This app's primary endpoint is same-hospital admission or hospitalization versus routine release home, after excluding other dispositions.

## Covariance

A way to describe how fitted model numbers move together.

This matters because coefficients are estimated from the same dataset. They are not always independent.

## Coefficient Draw

One simulated set of model coefficients.

The current app uses full coefficient draws, so the model numbers from the same draw stay together.

## Simulation Interval

A range from repeated model runs.

The app keeps the selected inputs fixed and reruns the estimate with many plausible coefficient draws. The interval shows how much the selected estimate can move because the fitted model numbers are uncertain.

## Want More Context?

- Logistic regression: [Google ML Crash Course](https://developers.google.com/machine-learning/crash-course/logistic-regression/sigmoid-function)
- Odds ratios: [UCLA odds ratio guide](https://stats.oarc.ucla.edu/other/mult-pkg/faq/general/faq-how-do-i-interpret-odds-ratios-in-logistic-regression/)
- ROC and AUC: [Google ROC/AUC guide](https://developers.google.com/machine-learning/crash-course/classification/roc-and-auc)
- Brier score: [UVA Library Brier score guide](https://library.virginia.edu/data/articles/a-brief-on-brier-scores)
- NHAMCS: [CDC NHAMCS Documentation](https://www.cdc.gov/nchs/nhamcs/documentation/index.html)
