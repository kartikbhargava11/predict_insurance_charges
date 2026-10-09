"""Clean the insurance data, compare models with 5-fold CV, save the best as model.joblib."""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "insurance.csv"
MODEL_PATH = ROOT / "model.joblib"

NUMERIC = ["age", "bmi", "children"]
CATEGORICAL = ["sex", "smoker", "region"]
TARGET = "charges"
SEED = 42
SEX_ALIASES = {"f": "female", "woman": "female", "m": "male", "man": "male"}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the data rules from CLAUDE.md."""
    df = df.copy()
    for col in CATEGORICAL:
        df[col] = df[col].str.strip().str.lower()
    df["sex"] = df["sex"].replace(SEX_ALIASES)
    if TARGET in df:
        df[TARGET] = df[TARGET].astype(str).str.replace("$", "", regex=False).astype(float)
    df = df.dropna()
    df = df[df["age"] > 0]
    df["children"] = df["children"].abs()
    return df.reset_index(drop=True)


def build_pipeline(model) -> Pipeline:
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    return Pipeline([("preprocess", preprocess), ("model", model)])


def main() -> None:
    df = clean(pd.read_csv(DATA_PATH))
    X, y = df[NUMERIC + CATEGORICAL], df[TARGET]
    print(f"Training rows after cleaning: {len(df)}")

    models = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(random_state=SEED),
        "GradientBoosting": GradientBoostingRegressor(random_state=SEED),
    }
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)

    rows = []
    for name, model in models.items():
        scores = cross_validate(
            build_pipeline(model), X, y, cv=cv,
            scoring={"r2": "r2", "mae": "neg_mean_absolute_error"},
        )
        rows.append({
            "model": name,
            "r2_mean": scores["test_r2"].mean(),
            "r2_std": scores["test_r2"].std(),
            "mae_mean": -scores["test_mae"].mean(),
            "mae_std": scores["test_mae"].std(),
        })

    results = pd.DataFrame(rows).sort_values("r2_mean", ascending=False).reset_index(drop=True)
    print("\n5-fold CV results (sorted by R²):")
    print(results.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    best_name = results.loc[0, "model"]
    best = build_pipeline(models[best_name]).fit(X, y)
    joblib.dump(best, MODEL_PATH)
    print(f"\nBest model: {best_name} -> saved to {MODEL_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
