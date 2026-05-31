"""
Future projection: roll features forward to 2050 and predict NDSI.

The trained Random Forest from `src.random_forest` is applied to a
synthetic future feature matrix — same spatial grid, monthly cadence,
years 2026 → 2050 — and the resulting per-pixel projections are
aggregated to district / domain level.

The published headline number is a **+20.8 % domain-mean increase in
NDSI by 2050** relative to the 2000–2026 climatology.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from src.config import PROJECTION_END_YEAR
from src.random_forest import build_feature_matrix, DEFAULT_FEATURES


def build_future_grid(
    locations: pd.DataFrame,
    start_year: int,
    end_year: int = PROJECTION_END_YEAR,
    months: Iterable[int] = range(1, 13),
    lat_col: str = "Latitude",
    lng_col: str = "Longitude",
) -> pd.DataFrame:
    """
    Cartesian product of locations × (year, month) to project on.

    Parameters
    ----------
    locations : DataFrame
        Must contain ``lat_col`` and ``lng_col`` columns. Extra columns
        (e.g. district name) are carried through.
    start_year, end_year : int
        Inclusive year range for the projection.
    months : iterable of int
        Months 1..12 to include. Default: all twelve.

    Returns
    -------
    Long-format DataFrame with one row per (location, year, month) and a
    ``date`` column set to the 15th of each month for downstream feature
    engineering.
    """
    years = list(range(start_year, end_year + 1))
    months = list(months)

    loc_keys = locations.reset_index(drop=True).copy()
    grids = []
    for y in years:
        for m in months:
            tmp = loc_keys.copy()
            tmp["date"] = pd.Timestamp(year=y, month=m, day=15)
            grids.append(tmp)

    out = pd.concat(grids, ignore_index=True)
    return out


def project(
    model: RandomForestRegressor,
    future_grid: pd.DataFrame,
    feature_cols: Iterable[str] = DEFAULT_FEATURES,
    date_col: str = "date",
) -> pd.DataFrame:
    """
    Apply the fitted model to a future grid.

    Returns
    -------
    Copy of `future_grid` with a new ``ndsi_pred`` column.
    """
    # Reuse the feature-building pipeline with a dummy target so we can
    # share the cyclic / cyclone-recency logic 1:1 with training.
    grid = future_grid.copy()
    grid["__dummy__"] = 0.0

    X, _ = build_feature_matrix(
        grid,
        target_col="__dummy__",
        date_col=date_col,
        feature_cols=feature_cols,
    )
    grid = grid.loc[X.index].copy()
    grid["ndsi_pred"] = model.predict(X)
    return grid.drop(columns="__dummy__")


def percent_change_summary(
    historical: pd.DataFrame,
    projection: pd.DataFrame,
    historical_value: str = "ndsi",
    projection_value: str = "ndsi_pred",
    group_by: str | None = None,
) -> pd.DataFrame:
    """
    Compute mean historical vs projected NDSI, optionally per group.

    Parameters
    ----------
    historical : DataFrame
        Observed time-series (e.g. 2000–2026 record).
    projection : DataFrame
        Output of `project` (e.g. 2026–2050 grid).
    historical_value, projection_value : str
        Column names containing the NDSI values in each frame.
    group_by : str, optional
        Column to group by (e.g. "district"). If None, returns a single
        domain-mean summary row.

    Returns
    -------
    DataFrame with ``mean_historical``, ``mean_projected``,
    ``absolute_change``, ``percent_change`` columns.
    """
    if group_by is None:
        h = float(historical[historical_value].mean())
        p = float(projection[projection_value].mean())
        return pd.DataFrame([{
            "scope": "domain",
            "mean_historical": h,
            "mean_projected": p,
            "absolute_change": p - h,
            "percent_change": 100 * (p - h) / h if h else float("nan"),
        }])

    h_grp = historical.groupby(group_by)[historical_value].mean()
    p_grp = projection.groupby(group_by)[projection_value].mean()
    out = pd.DataFrame({
        "mean_historical": h_grp,
        "mean_projected": p_grp,
    }).dropna()
    out["absolute_change"] = out["mean_projected"] - out["mean_historical"]
    out["percent_change"] = 100 * out["absolute_change"] / out["mean_historical"]
    return out.sort_values("percent_change", ascending=False).reset_index()


def identify_hotspots(
    projection: pd.DataFrame,
    percentile: float = 90,
    value_col: str = "ndsi_pred",
    lat_col: str = "Latitude",
    lng_col: str = "Longitude",
) -> pd.DataFrame:
    """
    Return locations whose mean projected NDSI is in the top percentile.

    Used to flag the southern Satkhira and coastal Bagerhat chronic-
    salinity hotspots reported in the paper.
    """
    by_loc = (
        projection.groupby([lat_col, lng_col])[value_col]
                  .mean()
                  .reset_index()
                  .rename(columns={value_col: "mean_ndsi_proj"})
    )
    cutoff = np.percentile(by_loc["mean_ndsi_proj"], percentile)
    hotspots = by_loc[by_loc["mean_ndsi_proj"] >= cutoff].copy()
    hotspots["percentile_cutoff"] = percentile
    hotspots["cutoff_value"] = float(cutoff)
    return hotspots.sort_values("mean_ndsi_proj", ascending=False).reset_index(drop=True)
