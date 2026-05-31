"""
Random Forest model for spatio-temporal NDSI prediction.

The model takes a tabular feature set — built from date, location,
cyclone recency, and seasonal indicators — and predicts NDSI as a
continuous target. The published model reports R² ≈ 0.496 and
RMSE ≈ 0.00539 (NDSI units) on the held-out fold.

API
---
- `build_feature_matrix(...)`  → assemble the X / y arrays from a time-series.
- `train_rf(...)`              → fit a single RandomForestRegressor.
- `kfold_evaluate(...)`        → k-fold CV with R² / RMSE / MAE per fold.
- `feature_importance(...)`    → tidy importance DataFrame for plotting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split

from src.config import KFOLD_SPLITS, RF_DEFAULTS, TEST_SIZE
from src.cyclone_analysis import years_since_last_cyclone


# ─────────────────────────────────────────────────────────────────────
# Feature engineering
# ─────────────────────────────────────────────────────────────────────
DEFAULT_FEATURES: tuple[str, ...] = (
    "year",
    "month",
    "doy",
    "Latitude",
    "Longitude",
    "years_since_cyclone",
    "month_sin",
    "month_cos",
)


def _cyclic_month(month: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Cyclic encoding of month so December → January wraps cleanly."""
    theta = 2 * np.pi * (month - 1) / 12
    return np.sin(theta), np.cos(theta)


def build_feature_matrix(
    df: pd.DataFrame,
    target_col: str = "ndsi",
    date_col: str = "date",
    feature_cols: Iterable[str] = DEFAULT_FEATURES,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Assemble the X / y arrays from a long-format NDSI dataframe.

    Required input columns:
        - `date_col` (datetime-coercible)
        - `Latitude`, `Longitude`
        - `target_col` (the NDSI target)

    Returns
    -------
    (X, y) — both NaN-free, aligned, ready for `train_rf`.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    df["year"] = df[date_col].dt.year
    df["month"] = df[date_col].dt.month
    df["doy"] = df[date_col].dt.dayofyear
    df["years_since_cyclone"] = years_since_last_cyclone(df[date_col]).replace(
        [np.inf, -np.inf], 100.0  # cap "never" at 100 yr for the RF
    )
    df["month_sin"], df["month_cos"] = _cyclic_month(df["month"])

    keep = list(feature_cols) + [target_col]
    df = df.dropna(subset=keep)
    return df[list(feature_cols)].copy(), df[target_col].copy()


# ─────────────────────────────────────────────────────────────────────
# Training
# ─────────────────────────────────────────────────────────────────────
@dataclass
class TrainResult:
    """Container for a single train/test fit."""
    model: RandomForestRegressor
    r2_train: float
    r2_test: float
    rmse_test: float
    mae_test: float
    n_train: int
    n_test: int


def train_rf(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = TEST_SIZE,
    random_state: int = 42,
    rf_kwargs: dict | None = None,
) -> TrainResult:
    """
    Fit a RandomForestRegressor with a held-out test split.

    Parameters
    ----------
    X, y : feature matrix / target series.
    test_size : float
        Fraction of data held out for the test metrics.
    random_state : int
        Reproducibility seed for the split.
    rf_kwargs : dict, optional
        Override the defaults in `src.config.RF_DEFAULTS`.

    Returns
    -------
    TrainResult.
    """
    kwargs = {**RF_DEFAULTS, **(rf_kwargs or {})}
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=random_state, shuffle=True,
    )
    model = RandomForestRegressor(**kwargs).fit(X_tr, y_tr)
    pred_tr = model.predict(X_tr)
    pred_te = model.predict(X_te)

    return TrainResult(
        model=model,
        r2_train=float(r2_score(y_tr, pred_tr)),
        r2_test=float(r2_score(y_te, pred_te)),
        rmse_test=float(np.sqrt(mean_squared_error(y_te, pred_te))),
        mae_test=float(mean_absolute_error(y_te, pred_te)),
        n_train=int(len(y_tr)),
        n_test=int(len(y_te)),
    )


def kfold_evaluate(
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = KFOLD_SPLITS,
    random_state: int = 42,
    rf_kwargs: dict | None = None,
) -> pd.DataFrame:
    """
    Stratified-by-time K-fold evaluation.

    Returns a DataFrame with per-fold R², RMSE, MAE, and the n of each fold.
    The aggregate row at the end gives mean ± std.
    """
    kwargs = {**RF_DEFAULTS, **(rf_kwargs or {})}
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    rows: list[dict] = []
    for i, (tr_idx, te_idx) in enumerate(kf.split(X), start=1):
        X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
        y_tr, y_te = y.iloc[tr_idx], y.iloc[te_idx]

        model = RandomForestRegressor(**kwargs).fit(X_tr, y_tr)
        pred = model.predict(X_te)
        rows.append({
            "fold": i,
            "n_test": len(y_te),
            "r2":   float(r2_score(y_te, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_te, pred))),
            "mae":  float(mean_absolute_error(y_te, pred)),
        })

    df = pd.DataFrame(rows)
    agg = {
        "fold": "mean ± std",
        "n_test": df["n_test"].sum(),
        "r2":   f"{df['r2'].mean():.4f} ± {df['r2'].std():.4f}",
        "rmse": f"{df['rmse'].mean():.5f} ± {df['rmse'].std():.5f}",
        "mae":  f"{df['mae'].mean():.5f} ± {df['mae'].std():.5f}",
    }
    return pd.concat([df, pd.DataFrame([agg])], ignore_index=True)


def feature_importance(model: RandomForestRegressor, feature_names: Iterable[str]) -> pd.DataFrame:
    """Tidy DataFrame of feature importances, sorted descending."""
    return (
        pd.DataFrame({
            "feature": list(feature_names),
            "importance": model.feature_importances_,
        })
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
