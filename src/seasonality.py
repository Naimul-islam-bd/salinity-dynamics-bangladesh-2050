"""
Seasonal climatology and anomaly detection.

The paper's headline novel finding is a *late-monsoon (August) salinity
peak* in the moribund delta — a result that challenges the conventional
dry-season-only salinity narrative. This module implements the
deseasonalising and anomaly-surfacing logic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_temporal_features(
    df: pd.DataFrame,
    date_col: str = "date",
) -> pd.DataFrame:
    """
    Add `year`, `month`, and `doy` (day-of-year) columns from a date.

    Returns a copy; the original is untouched.
    """
    out = df.copy()
    dt = pd.to_datetime(out[date_col])
    out["year"] = dt.dt.year
    out["month"] = dt.dt.month
    out["doy"] = dt.dt.dayofyear
    return out


def monthly_climatology(
    ts: pd.DataFrame,
    value_col: str = "ndsi_mean",
    date_col: str = "date",
) -> pd.DataFrame:
    """
    Compute the long-term mean, std, and count for each calendar month.

    Returns
    -------
    DataFrame indexed by month (1..12) with columns
    ``mean``, ``std``, ``count``.
    """
    ts = add_temporal_features(ts, date_col=date_col)
    agg = (
        ts.groupby("month")[value_col]
          .agg(["mean", "std", "count"])
          .sort_index()
    )
    return agg


def deseasonalise(
    ts: pd.DataFrame,
    value_col: str = "ndsi_mean",
    date_col: str = "date",
) -> pd.DataFrame:
    """
    Subtract the monthly climatological mean from each observation.

    Adds a ``ndsi_anomaly`` column to a copy of the input.
    """
    ts = add_temporal_features(ts, date_col=date_col)
    clim = monthly_climatology(ts, value_col=value_col, date_col=date_col)
    ts = ts.merge(
        clim["mean"].rename("clim_mean"),
        left_on="month", right_index=True, how="left",
    )
    ts["ndsi_anomaly"] = ts[value_col] - ts["clim_mean"]
    return ts.drop(columns=["clim_mean"])


def annual_august_anomaly(
    ts: pd.DataFrame,
    value_col: str = "ndsi_mean",
    date_col: str = "date",
) -> pd.DataFrame:
    """
    For each year, return the August-mean NDSI and its anomaly versus
    the long-term August climatology.

    This isolates the August-peak signal that the paper documents.
    """
    ts = deseasonalise(ts, value_col=value_col, date_col=date_col)
    aug = ts[ts["month"] == 8]
    if aug.empty:
        return pd.DataFrame(columns=["year", "august_mean", "august_anomaly", "n_obs"])

    grouped = (
        aug.groupby("year")
           .agg(august_mean=(value_col, "mean"),
                august_anomaly=("ndsi_anomaly", "mean"),
                n_obs=(value_col, "count"))
           .reset_index()
    )
    return grouped


def rolling_mean(
    ts: pd.DataFrame,
    value_col: str = "ndsi_mean",
    date_col: str = "date",
    window_months: int = 12,
) -> pd.Series:
    """
    Centred rolling-mean smoother (NaN-safe).

    Used to draw the long-term trend overlay on top of the noisy
    raw time-series.
    """
    ts = ts.sort_values(date_col).copy()
    ts = ts.set_index(pd.to_datetime(ts[date_col]))
    return ts[value_col].rolling(f"{window_months * 30}D", center=True, min_periods=3).mean()
