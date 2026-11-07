# HackMatrix URL ML artifacts

This directory contains the supplied model bundle:

- `url_xgb.joblib` — numeric URL-feature XGBoost classifier
- `url_char_logreg.joblib` — character n-gram LogisticRegression classifier
- `url_char_vectorizer.joblib` — fitted TF-IDF character vectorizer
- `metadata.json` — feature names/order, class meaning, ensemble rule and reported metrics

The engine combines the two class-1 probabilities equally:

`P(legitimate) = 0.5 * P_XGB(legitimate) + 0.5 * P_char_LR(legitimate)`

Class 1 is explicitly labelled `legitimate`; HackMatrix risk is `1 - P(legitimate)`.

**Dependency pin:** `url_xgb.joblib` is a legacy-format booster; xgboost 3.x fails to
load it with `XGBoostError: input stream corrupted`. Both requirement files therefore pin
`xgboost>=2.1,<3`. Re-export the model with `Booster.save_model` before widening that pin.

**Feature-extraction limitation:** the metadata provides the 27 numeric feature names and
their order, but not the exact training-time feature extraction source. `engines/ml_engine.py`
implements deterministic URL parsing/counting for those fields. Confirm these definitions
against the training code that produced this artifact before relying on the reported offline
metrics in production. The artifact bundle is not the same format as the older
`backend/ml/colab_train.ipynb` export described in the original codebase.

Joblib files are pickle-based executable artifacts. Load only trusted model files.
