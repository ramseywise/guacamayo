---
name: review-leakage
description: >
  Leakage Dimension Checklist — dimension checklist read by the scan-leakage agent (.claude/agents/leakage.md).
  Conditional dimension (tabular-ML code only). Reference material, not invoked directly.
allowed-tools: Read
---

# Leakage Dimension Checklist

Agent: `scan-leakage` | ID prefix: `LK-` | Conditional (`is_ml_code`)

Used by: `.claude/agents/leakage.md`

Activation: dispatched only when `detect-signals` reports `is_ml_code: true`.

This is **tabular-ML leakage** — train/test contamination in supervised learning. Not
LLMs, not prompt content. A leaked feature does not raise: it returns AUC 0.97 and reads
as success. Correctness owns whether the code does what it says; this dimension owns
whether the number it reports means what it claims.

## The One Question

- For every place a model or transform is **fitted**, and every place data is **split**:
  *at the moment this line runs, what does it know that it would not know at prediction
  time?* Anything at all is a finding.
- Read the ordering, not just the calls — `fit_transform` before `train_test_split` is two
  valid lines whose order is the bug.

## Target Leakage

- Are post-outcome columns kept in the feature matrix (`settlement_date`,
  `amount_recovered`, `closed_reason`, `days_to_payment`, `*_final`, `*_actual`,
  `*_outcome`)?
- Was what the matrix *keeps* checked, not only what it drops? `df.drop(columns=["label"])`
  keeps every other post-outcome column.
- Are there proxies deterministic given the target?
- Is a single feature suspiciously strong (feature-target correlation >~0.95, unexplained
  AUC >~0.97)?
- Are aggregates or target encodings computed over the full frame?

## Temporal Leakage

- Is a random `train_test_split` / `KFold` / `StratifiedKFold` used on time-structured data
  (a date, cohort, or period column exists) — training on the future to predict the past?
- Are rolling or lag features computed without an `as_of` cutoff?
- Are imputation or scaling statistics drawn from the whole time range then applied to an
  earlier fold?

## Group Leakage

- Is the same entity on both sides of the split — one debtor with several accounts, one
  patient with several visits, one user with several sessions — so the model memorises the
  entity rather than the pattern?
- The shape: a repeated `*_id` column present while the split ignores it, and no
  `GroupKFold` / `GroupShuffleSplit`.

## Fit-Before-Split Ordering

- Is there any `fit` / `fit_transform` on the full frame before the split line (scalers,
  imputers, encoders, feature selectors, PCA)?
- Are transform objects fitted outside a `Pipeline` and reused across folds?
- Is target encoding fitted outside the CV fold?
- Is feature selection (top-k by target correlation) run over the full dataset before CV?

## Resampling Outside the Fold

- Is SMOTE, over/undersampling, or Tomek/ENN applied before the split, or to validation
  data at all?
- Resampling belongs inside the fold on training data only: a sampler in an `imblearn`
  pipeline is the correct shape; a sampler called on `df` is not.

## Train/Serve Skew

- Does inference recompute a feature the training path computed differently (same name,
  different formula)?
- Is a model saved without its transform, so serving re-implements preprocessing by hand?
- Is there a feature-name or schema check at load time, or can column order / renamed
  columns silently produce wrong predictions?

## What NOT to Flag

- Exploratory or notebook code that never fits a scored model; a transform fitted on the
  full frame where there is demonstrably no test split and no scoring claim (EDA is not
  leakage).
- Deliberate full-data refits **after** evaluation, where the code says so, provided the
  reported metric came from before it.
- Pre-existing leakage the diff did not touch, unless the change makes it load-bearing —
  then it carries `pre_existing: true`.
- A high AUC the code or its comments explain (a genuinely separable problem, a synthetic
  fixture). Say what would distinguish the two.

## Evidence Standard

- **verified**: ordering confirmed by line numbers (e.g. `fit_transform` at :42 precedes
  `train_test_split` at :57)
- **supported**: strong evidence, one assumption remains
- **hypothesis**: ordering visible but a column's post-outcome status unconfirmed — say so
- Cite the **fit** line for an ordering finding — that is where the leak happens — and name
  the split line in the observation
- Rank by blast radius: a leak inflating the headline metric outranks one inflating a
  single feature's importance
- An empty changed-file list is a failure to report as such, **not** a clean review
