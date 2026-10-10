"""Clean the insurance data, compare models with 5-fold CV, save the best as model.joblib."""

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "insurance.csv"
MODEL_PATH = ROOT / "model.joblib"

NUMERIC = ["age", "bmi", "children"]
CATEGORICAL = ["sex", "smoker", "region"]
TARGET = "charges"
SEED = 42
SEX_ALIASES = {"f": "female", "woman": "female", "m": "male", "man": "male"}
INTERACTION = "smoker_bmi"
MIN_MAE_GAIN = 0.05  # serve the interaction model only if it cuts MAE by at least 5%


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
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


def add_smoker_bmi(X: pd.DataFrame) -> pd.DataFrame:
    """Add smoker × bmi: bmi for smokers, 0 for non-smokers."""
    X = X.copy()
    X[INTERACTION] = X["bmi"] * (X["smoker"] == "yes")
    return X


def build_pipeline(model, with_interaction: bool = False) -> Pipeline:
    numeric = NUMERIC + [INTERACTION] if with_interaction else NUMERIC
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    steps = [("preprocess", preprocess), ("model", model)]
    # Inside the pipeline, so the API sends the same 6 fields either way.
    if with_interaction:
        steps.insert(0, ("interaction", FunctionTransformer(add_smoker_bmi)))
    return Pipeline(steps)


def choose(results: pd.DataFrame) -> tuple[pd.Series, str]:
    """Pick the best base model unless the best interaction model beats its MAE by MIN_MAE_GAIN."""
    base = results[~results["interaction"]].nsmallest(1, "mae_mean").iloc[0]
    inter = results[results["interaction"]].nsmallest(1, "mae_mean").iloc[0]
    gain = 1 - inter["mae_mean"] / base["mae_mean"]
    if gain >= MIN_MAE_GAIN:
        return inter, (f"{inter['model']} +smoker×bmi cuts MAE by {gain:.1%} vs {base['model']} "
                       f"(>= {MIN_MAE_GAIN:.0%} required)")
    return base, (f"+smoker×bmi only changes MAE by {gain:.1%} vs {base['model']} "
                  f"(< {MIN_MAE_GAIN:.0%} required), so keep the simpler model")


def main() -> None:
    df = clean_data(pd.read_csv(DATA_PATH))
    X, y = df[NUMERIC + CATEGORICAL], df[TARGET]
    print(f"Training rows after cleaning: {len(df)}")

    models = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(random_state=SEED),
        "GradientBoosting": GradientBoostingRegressor(random_state=SEED),
    }
    cv = KFold(n_splits=5, shuffle=True, random_state=SEED)

    rows = []
    for with_interaction in (False, True):
        for name, model in models.items():
            scores = cross_validate(
                build_pipeline(model, with_interaction), X, y, cv=cv,
                scoring={"r2": "r2", "mae": "neg_mean_absolute_error"},
            )
            rows.append({
                "model": name,
                "interaction": with_interaction,
                "r2_mean": scores["test_r2"].mean(),
                "r2_std": scores["test_r2"].std(),
                "mae_mean": -scores["test_mae"].mean(),
                "mae_std": scores["test_mae"].std(),
            })

    results = pd.DataFrame(rows).sort_values("mae_mean").reset_index(drop=True)
    table = results.assign(features=results["interaction"].map({False: "base", True: "+smoker×bmi"}))
    cols = ["model", "features", "r2_mean", "r2_std", "mae_mean", "mae_std"]
    print("\n5-fold CV results (sorted by MAE, lower is better):")
    print(table[cols].to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    chosen, reason = choose(results)
    best = build_pipeline(models[chosen["model"]], chosen["interaction"]).fit(X, y)
    joblib.dump(best, MODEL_PATH)
    features = "+smoker×bmi" if chosen["interaction"] else "base"
    print(f"\nChosen: {chosen['model']} ({features}) -> saved to {MODEL_PATH.relative_to(ROOT)}")
    print(f"Why: {reason}")


if __name__ == "__main__":
    # Run via the importable module, so the pickled add_smoker_bmi points to src.train
    # (not __main__) and the API can load model.joblib.
    sys.path.insert(0, str(ROOT))
    from src.train import main as run
    run()
