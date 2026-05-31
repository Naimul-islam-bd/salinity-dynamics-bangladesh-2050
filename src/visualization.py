"""
Plotting helpers shared by every notebook.

All functions accept an optional ``save_to`` path; when given, the figure
is written at 300 dpi for publication and the function returns the Path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import CYCLONE_EVENTS

# A small palette used throughout — colourblind-safe, print-readable.
PALETTE = {
    "primary":   "#2166AC",
    "accent":    "#D6604D",
    "muted":     "#9E9E9E",
    "highlight": "#1d7676",
    "warning":   "#E69F00",
    "background": "#FAFAFA",
}


def _maybe_save(fig, save_to: Optional[str | Path]) -> Optional[Path]:
    """Common save+return wrapper."""
    if save_to is None:
        return None
    save_to = Path(save_to)
    save_to.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_to, dpi=300, bbox_inches="tight")
    return save_to


def plot_timeseries(
    ts: pd.DataFrame,
    value_col: str = "ndsi_mean",
    date_col: str = "date",
    rolling: pd.Series | None = None,
    annotate_cyclones: bool = True,
    title: str = "NDSI mean — southwest Bangladesh study domain",
    save_to: Optional[str | Path] = None,
):
    """
    The headline time-series plot: raw NDSI scatter + smoothed trend +
    vertical lines on cyclone landfalls.
    """
    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor("white")

    ax.scatter(
        ts[date_col], ts[value_col],
        color=PALETTE["primary"], alpha=0.45, s=14,
        label=f"Raw observations (n={len(ts)})",
    )

    if rolling is not None and not rolling.empty:
        ax.plot(
            rolling.index, rolling.values,
            color=PALETTE["accent"], linewidth=2.0,
            label="12-month rolling mean",
        )

    if annotate_cyclones:
        for ev in CYCLONE_EVENTS:
            ax.axvline(
                pd.Timestamp(ev.landfall_date),
                color=PALETTE["muted"], linestyle="--", linewidth=0.8, alpha=0.7,
            )
            ax.text(
                pd.Timestamp(ev.landfall_date), ax.get_ylim()[1],
                ev.name, rotation=90, va="top", ha="right",
                fontsize=8, color=PALETTE["muted"], alpha=0.9,
            )

    ax.set_xlabel("Date")
    ax.set_ylabel("NDSI")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="best", framealpha=0.9)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.tight_layout()
    _maybe_save(fig, save_to)
    return fig, ax


def plot_monthly_climatology(
    clim: pd.DataFrame,
    title: str = "Monthly NDSI climatology — southwest Bangladesh (2000–2026)",
    save_to: Optional[str | Path] = None,
):
    """Bar chart of monthly mean ± std. Highlights August in accent colour."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    colors = [PALETTE["accent"] if m == 8 else PALETTE["primary"]
              for m in range(1, 13)]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("white")

    ax.bar(months, clim["mean"], yerr=clim["std"],
           color=colors, alpha=0.85, capsize=4,
           edgecolor="white", linewidth=0.6)
    ax.set_xlabel("Month")
    ax.set_ylabel("NDSI (mean ± 1 σ)")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    _maybe_save(fig, save_to)
    return fig, ax


def plot_cyclone_effects(
    event_table: pd.DataFrame,
    title: str = "Cyclone-attributable NDSI change (post − pre, 90-day windows)",
    save_to: Optional[str | Path] = None,
):
    """
    Forest-plot-style figure: one row per cyclone, point = mean diff,
    horizontal bars = bootstrap CI.
    """
    df = event_table.dropna(subset=["mean_diff"]).copy()
    df = df.sort_values("landfall_date")

    fig, ax = plt.subplots(figsize=(9, 1 + 0.6 * len(df)))
    fig.patch.set_facecolor("white")

    y = np.arange(len(df))
    ax.hlines(y, df["ci_lower"], df["ci_upper"],
              color=PALETTE["primary"], linewidth=3, alpha=0.75)
    ax.scatter(df["mean_diff"], y, color=PALETTE["accent"],
               s=60, zorder=3, label="Mean post − pre")
    ax.axvline(0, color=PALETTE["muted"], linestyle="--", linewidth=0.8)

    labels = [f"{r['event']}\n({r['landfall_date']})" for _, r in df.iterrows()]
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("ΔNDSI  (95 % bootstrap CI)")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.invert_yaxis()
    ax.legend(loc="lower right")

    plt.tight_layout()
    _maybe_save(fig, save_to)
    return fig, ax


def plot_feature_importance(
    importance: pd.DataFrame,
    title: str = "Random Forest feature importance",
    save_to: Optional[str | Path] = None,
):
    """Horizontal bar chart of RF feature importances."""
    fig, ax = plt.subplots(figsize=(8, 4 + 0.25 * len(importance)))
    fig.patch.set_facecolor("white")

    ax.barh(importance["feature"], importance["importance"],
            color=PALETTE["highlight"], alpha=0.9, edgecolor="white")
    ax.invert_yaxis()
    ax.set_xlabel("Importance (Gini reduction)")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(axis="x", linestyle="--", alpha=0.4)

    plt.tight_layout()
    _maybe_save(fig, save_to)
    return fig, ax


def plot_projection_hotspots(
    hotspots: pd.DataFrame,
    lat_col: str = "Latitude",
    lng_col: str = "Longitude",
    value_col: str = "mean_ndsi_proj",
    title: str = "2050 projected NDSI hotspots (top 10 %)",
    save_to: Optional[str | Path] = None,
):
    """Scatter of hotspot coordinates coloured by projected NDSI."""
    fig, ax = plt.subplots(figsize=(8, 9))
    fig.patch.set_facecolor("white")

    sc = ax.scatter(
        hotspots[lng_col], hotspots[lat_col],
        c=hotspots[value_col], cmap="YlOrRd",
        s=40, edgecolor="white", linewidth=0.4,
    )
    cbar = plt.colorbar(sc, ax=ax, shrink=0.7)
    cbar.set_label("Mean projected NDSI (2026–2050)")

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_aspect("equal", adjustable="datalim")

    plt.tight_layout()
    _maybe_save(fig, save_to)
    return fig, ax


def plot_august_anomaly(
    annual_aug: pd.DataFrame,
    title: str = "August NDSI anomaly — moribund delta (2000–2026)",
    save_to: Optional[str | Path] = None,
):
    """Time-series of annual August NDSI anomaly with zero reference line."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor("white")

    colors = [PALETTE["accent"] if v > 0 else PALETTE["primary"]
              for v in annual_aug["august_anomaly"]]
    ax.bar(annual_aug["year"], annual_aug["august_anomaly"],
           color=colors, alpha=0.85, edgecolor="white")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Year")
    ax.set_ylabel("August NDSI anomaly")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    _maybe_save(fig, save_to)
    return fig, ax
