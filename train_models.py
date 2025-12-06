import os
import pickle
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.impute import SimpleImputer
from sklearn.exceptions import NotFittedError
from scipy.sparse import hstack
from pandas.api.types import is_numeric_dtype

# IMPORTANT:
# After creating this file, run manually:
#     python train_models.py

UNIFIED_PATH = "unified_training.csv"
MODEL_DIR = "models"
TEXT_COL = "free_text"
TARGETS = ["stress_score", "anxiety_score", "depression_score"]


def load_data():
    df = pd.read_csv(UNIFIED_PATH)
    df = df.dropna(subset=TARGETS, how="all")
    return df


# NOTE:
# This function intentionally fits TF-IDF on a dummy token ("noop")
# when no real text is available to avoid empty-vocabulary errors.
def build_tfidf(df: pd.DataFrame, text_present: bool):
    vectorizer = TfidfVectorizer(max_features=200)

    if not text_present:
        vectorizer.fit(["noop"])
        return vectorizer

    texts = df[TEXT_COL].fillna("").astype(str).tolist()
    cleaned = [t.strip() for t in texts if t.strip() != ""]

    if len(cleaned) == 0:
        vectorizer.fit(["noop"])
        return vectorizer

    vectorizer.fit(cleaned)
    return vectorizer


def build_preprocessor(df: pd.DataFrame):
    target_cols = TARGETS + ["source_dataset"]
    feature_cols = [c for c in df.columns if c not in target_cols]

    text_present = TEXT_COL in feature_cols
    if text_present:
        feature_cols.remove(TEXT_COL)

    cat_cols = [c for c in feature_cols if df[c].dtype == object]
    num_cols = [c for c in feature_cols if is_numeric_dtype(df[c])]

    numeric_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, num_cols),
            ("cat", categorical_pipeline, cat_cols),
        ],
        remainder="drop",
    )

    return preprocessor, text_present, feature_cols


def train_one(df: pd.DataFrame, preprocessor, vectorizer, text_present: bool, target: str):
    summary = {"target": target, "rows": 0, "features": 0, "mae": None, "skipped": False}
    df_t = df.dropna(subset=[target]).copy()
    if df_t.empty or len(df_t) < 20:
        summary["skipped"] = True
        return None, summary, preprocessor, vectorizer

    y = pd.to_numeric(df_t[target], errors="coerce")
    mask = y.notna()
    df_t = df_t[mask]
    y = y[mask]
    if len(df_t) < 20:
        summary["skipped"] = True
        return None, summary, preprocessor, vectorizer

    target_cols = TARGETS + ["source_dataset"]
    feature_cols = [c for c in df_t.columns if c not in target_cols]
    use_text = text_present and TEXT_COL in feature_cols
    if use_text:
        feature_cols.remove(TEXT_COL)

    X_tab = df_t[feature_cols].copy()
    X_text = df_t[TEXT_COL].fillna("").astype(str) if use_text else pd.Series([""] * len(df_t))

    X_tab_transformed = preprocessor.fit_transform(X_tab)

    try:
        X_text_vec = vectorizer.transform(X_text)
    except Exception:
        vectorizer.fit(["noop"])
        X_text_vec = vectorizer.transform(X_text)

    X_all = hstack([X_tab_transformed, X_text_vec])

    model = HistGradientBoostingRegressor(max_depth=6, learning_rate=0.05)
    try:
        model.fit(X_all.toarray() if hasattr(X_all, "toarray") else X_all, y)
        preds = model.predict(X_all.toarray() if hasattr(X_all, "toarray") else X_all)
        mae = mean_absolute_error(y, preds)
    except Exception:
        summary["skipped"] = True
        return None, summary, preprocessor, vectorizer

    summary.update({"rows": len(df_t), "features": X_all.shape[1], "mae": mae})
    return model, summary, preprocessor, vectorizer


def save_artifacts(preprocessor, vectorizer, models):
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(os.path.join(MODEL_DIR, "preprocessor.pkl"), "wb") as f:
        pickle.dump(preprocessor, f)
    with open(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"), "wb") as f:
        pickle.dump(vectorizer, f)
    for name, model in models.items():
        with open(os.path.join(MODEL_DIR, f"{name}.pkl"), "wb") as f:
            pickle.dump(model, f)


def main():
    df = load_data()
    preprocessor, text_present, feature_cols = build_preprocessor(df)
    vectorizer = build_tfidf(df, text_present)

    summaries = []
    models = {}

    for target in TARGETS:
        model, info, preprocessor, vectorizer = train_one(df, preprocessor, vectorizer, text_present, target)
        summaries.append(info)
        if not info["skipped"] and model is not None:
            models[target.replace("_score", "_model")] = model

    save_artifacts(preprocessor, vectorizer, models)

    print("Training summary:")
    for s in summaries:
        status = "skipped" if s["skipped"] else "trained"
        print(
            f"{s['target']}: {status}, rows={s.get('rows')}, features={s.get('features')}, "
            f"train MAE={s.get('mae')}"
        )


if __name__ == "__main__":
    main()

