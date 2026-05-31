"""
Cyclone-event attribution for surface salinity change.

For each major cyclone in `src.config.CYCLONE_EVENTS`, this module
compares the mean NDSI in the *N* days before landfall against the
mean in the *N* days after landfall, with non-parametric bootstrap
confidence intervals on the difference.

Why bootstrap? The pre/post windows are short and the residual
distribution after deseasonalising is heavy-tailed; a parametric
t-test would over-narrow the CIs.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

import numpy as np
import pandas as pd

from src.config import CYCLONE_EVENTS, CYCLONE_WINDOW_DAYS, CycloneEvent


def _window_mask(dates: pd.Series, centre: date, window_days: int, side: str) -> pd.Series:
    """Build a boolean mask for a pre or post window around `centre`."""
    if side == "pre":
        lo = pd.Timestamp(centre) - pd.Timedelta(days=window_days)
        hi = pd.Timestamp(centre)
        return (dates >= lo) & (dates < hi)
    if side == "post":
        lo = pd.Timestamp(centre)
        hi = pd.Timestamp(centre) + pd.Timedelta(days=window_days)
        return (dates > lo) & (dates <= hi)
    raise ValueError("side must be 'pre' or 'post'")


def bootstrap_diff_ci(
    pre: np.ndarray,
    post: np.ndarray,
    n_resamples: int = 5_000,
    confidence: float = 0.95,
    random_state: int = 42,
) -> dict:
    """
    Bootstrap a confidence interval on the post-minus-pre mean difference.

    Parameters
    ----------
    pre, post : array-like
        Samples drawn from the two windows.
    n_resamples : int
        Number of bootstrap iterations.
    confidence : float
        e.g. 0.95 for a 95 % two-sided CI.
    random_state : int
        Seed for reproducibility.

    Returns
    -------
    {"mean_diff", "ci_lower", "ci_upper", "n_pre", "n_post"}
    """
    pre = np.asarray(pre, dtype=float)
    post = np.asarray(post, dtype=float)
    pre = pre[~np.isnan(pre)]
    post = post[~np.isnan(post)]

    if len(pre) == 0 or len(post) == 0:
        return {
            "mean_diff": float("nan"),
            "ci_lower": float("nan"),
            "ci_upper": float("nan"),
            "n_pre": len(pre),
            "n_post": len(post),
        }

    rng = np.random.default_rng(random_state)
    diffs = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        a = rng.choice(pre,  size=len(pre),  replace=True)
        b = rng.choice(post, size=len(post), replace=True)
        diffs[i] = b.mean() - a.mean()

    alpha = (1 - confidence) / 2
    return {
        "mean_diff": float(post.mean() - pre.mean()),
        "ci_lower":  float(np.quantile(diffs, alpha)),
        "ci_upper":  float(np.quantile(diffs, 1 - alpha)),
        "n_pre": int(len(pre)),
        "n_post": int(len(post)),
    }


def analyse_event(
    ndsi_ts: pd.DataFrame,
    event: CycloneEvent,
    window_days: int = CYCLONE_WINDOW_DAYS,
    date_col: str = "date",
    value_col: str = "ndsi_mean",
) -> dict:
    """
    Compute pre/post statistics for a single cyclone event.

    Parameters
    ----------
    ndsi_ts : DataFrame
        Time-series of NDSI values with ``date_col`` and ``value_col``.
    event : CycloneEvent
    window_days : int
        Half-window length in days (default uses configured value).

    Returns
    -------
    Dict with event metadata + bootstrap stats.
    """
    pre_mask = _window_mask(ndsi_ts[date_col], event.landfall_date, window_days, "pre")
    post_mask = _window_mask(ndsi_ts[date_col], event.landfall_date, window_days, "post")

    pre_vals = ndsi_ts.loc[pre_mask, value_col].to_numpy()
    post_vals = ndsi_ts.loc[post_mask, value_col].to_numpy()

    boot = bootstrap_diff_ci(pre_vals, post_vals)

    return {
        "event": event.name,
        "landfall_date": event.landfall_date.isoformat(),
        "season": event.season,
        "window_days": window_days,
        "pre_mean":  float(np.nanmean(pre_vals))  if len(pre_vals)  else float("nan"),
        "post_mean": float(np.nanmean(post_vals)) if len(post_vals) else float("nan"),
        **boot,
    }


def analyse_all_events(
    ndsi_ts: pd.DataFrame,
    events: Sequence[CycloneEvent] = CYCLONE_EVENTS,
    window_days: int = CYCLONE_WINDOW_DAYS,
    date_col: str = "date",
    value_col: str = "ndsi_mean",
) -> pd.DataFrame:
    """
    Run ``analyse_event`` over every cyclone in `events`.

    Returns a tidy DataFrame, one row per event.
    """
    rows = [
        analyse_event(ndsi_ts, e, window_days, date_col, value_col)
        for e in events
    ]
    return pd.DataFrame(rows)


def years_since_last_cyclone(
    dates: pd.Series,
    events: Sequence[CycloneEvent] = CYCLONE_EVENTS,
) -> pd.Series:
    """
    Vectorised utility: for each timestamp, return years since the most
    recent prior cyclone landfall (inf if none).

    Used as a Random Forest feature in `src.random_forest`.
    """
    landfalls = sorted(pd.Timestamp(e.landfall_date) for e in events)

    def _years_since(t: pd.Timestamp) -> float:
        prior = [d for d in landfalls if d <= t]
        if not prior:
            return float("inf")
        return (t - prior[-1]).days / 365.25

    return pd.to_datetime(dates).map(_years_since)
