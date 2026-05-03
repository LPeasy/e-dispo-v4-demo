# Uncertainty Simulation Method

## Part 1: Plain-English Explanation

The simulation can answer two different questions, and they should not be mixed.

The first question is: for this exact run, how uncertain is the model estimate? If the user enters age, heart rate, pain severity, fever, and vomiting, those inputs should stay fixed. The simulation should only vary the fitted model numbers. That shows how much the estimate can move because the model coefficients are uncertain.

The second question is: what range of estimates appears across different people in the source sample? That is a population or case-mix question. For that question, it can make sense to use the actual observed ages, heart rates, pain values, fever values, and vomiting values from the sample.

A simple way to think about it:

- Selected-run uncertainty is like driving one fixed route with an uncertain map. The route stays the same, but the map measurements may be a little off.
- Source-sample variation is like sampling many different routes. That tells you about the spread across routes, not the uncertainty for one route.

For the app's selected run, the better approach is to keep the user-entered inputs fixed and vary the model coefficients together. Empirical input distributions are useful for a separate educational source-cohort view, but they should not be used as the selected-run interval.

## Part 2: Technical Explanation

The previous app simulation used Latin Hypercube Sampling over active logistic terms. For each active term, the app sampled values independently as:

```text
sampled_term = coefficient_mean + z_quantile * coefficient_standard_error
```

Then it summed the sampled terms and transformed the result with the logistic function. This propagated coefficient uncertainty, but it treated every active coefficient as independent.

That independence assumption is the main limitation. Fitted regression coefficients are usually correlated because they are estimated from the same data and model matrix. Drawing each coefficient separately can distort the spread of the final linear predictor, especially when predictors overlap or compensate for one another.

The preferred selected-run method is to use complete coefficient-vector draws. Each simulation row should select one full draw containing the intercept, age coefficient, pain coefficients, fever coefficient, vomiting coefficient, and tachycardia coefficient from the same `draw_id`. The fixed user inputs are then applied to that full vector:

```text
logit = intercept_draw
      + age_centered_draw * (age - 42)
      + tachycardia_burden_draw * max(HR - 100, 0) / 10
      + active symptom and pain coefficients from the same draw_id
```

This keeps the interpretation focused: the interval represents fitted-model uncertainty for the selected input profile. It does not represent individual-level certainty, clinical safety, diagnosis, triage, treatment, or discharge guidance.

Empirical input distributions answer a different question. They can describe source-sample or target-population case-mix variation, especially when row-level resampling preserves realistic combinations of inputs. But empirical input resampling should be shown as a separate source-cohort variation view, not folded into the selected-run uncertainty interval.

Project rule: after fitting, independent coefficient draws should be used only when covariance or posterior/bootstrap draws are unavailable, and that limitation must be explicit. When coefficient-vector draws or a covariance matrix are available, selected-run simulation should use those joint draws instead of independent mean/SE sampling.
