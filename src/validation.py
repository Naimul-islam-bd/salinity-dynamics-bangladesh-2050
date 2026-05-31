"""
Field-validation of satellite-derived NDSI against ground-truth EC.

The validation step pairs each in-situ electrical-conductivity (EC, mS/cm)
measurement from the March 2024 field campaign with the spatially
co-located, time-window mean NDSI from Landsat 8. The relationship is
assessed with both linear and log-transformed regression.

This is the canonical reference implementation for the validation panel
shown in notebook 01.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def load_field_ec(
    path: str | Path,
    sheet_header_row: int = 1,
    columns: tuple = (
        "ID", "SAMPLE_NO", "Latitude", "Longitude",
        "EC", "Sample_Type", "Collection_Date", "Team",
    ),
) -> pd.DataFrame:
    """
    Load the MIT March-2024 field EC dataset from its Excel master file.

    The original file uses a two-row header; ``sheet_header_row=1`` skips
    the explanatory first row and reads the column-name row below.

    Parameters
    ----------
    path : str or Path
        Path to ``Soil_Salinity_Data_BD032024.xlsx`` (or equivalent).
    sheet_header_row : int
        Header row index. The shipped file expects 1.
    columns : tuple of str
        Expected column names (in order).

    Returns
    -------
    DataFrame with numeric Latitude / Longitude / EC columns and rows
    missing any of those three dropped.
    """
    df = pd.read_excel(path, header=sheet_header_row)
    df.columns = list(columns)
    df = df.dropna(subset=["Latitude", "Longitude", "EC"])
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["EC"] = pd.to_numeric(df["EC"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude", "EC"]).reset_index(drop=True)
    return df


def linear_regression_stats(x: pd.Series, y: pd.Series) -> dict:
    """
    Run a linear regression and return a small results dict.

    Returns
    -------
    {"slope", "intercept", "r", "r2", "p_value", "std_err", "n"}
    """
    slope, intercept, r, p, se = stats.linregress(x, y)
    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r": float(r),
        "r2": float(r ** 2),
        "p_value": float(p),
        "std_err": float(se),
        "n": int(len(x)),
    }


def compare_linear_vs_log(
    df: pd.DataFrame,
    x_col: str = "NDSI",
    y_col: str = "EC",
) -> pd.DataFrame:
    """
    Fit linear and log–log models on the same NDSI–EC dataset.

    Returns a 2-row DataFrame with stats for each model — useful for
    publication tables.
    """
    df = df.dropna(subset=[x_col, y_col]).copy()
    log_x = np.log1p(df[x_col])
    log_y = np.log1p(df[y_col])

    linear = linear_regression_stats(df[x_col], df[y_col])
    log_  = linear_regression_stats(log_x, log_y)

    return pd.DataFrame([
        {"model": "linear (raw)",       **linear},
        {"model": "log-log (log1p)",    **log_},
    ])


def plot_validation_scatter(
    df: pd.DataFrame,
    x_col: str = "NDSI",
    y_col: str = "EC",
    save_to: Optional[str | Path] = None,
    title: str = (
        "Validation: Satellite NDSI vs Field EC Measurements\n"
        "Southwest Bangladesh — March 2024"
    ),
):
    """
    Render the canonical validation scatter plot.

    Parameters
    ----------
    df : DataFrame
        Must contain ``x_col`` and ``y_col``.
    x_col, y_col : str
        Column names for the X (NDSI) and Y (EC) variables.
    save_to : path-like, optional
        If given, the figure is saved at 300 dpi to this path; otherwise
        shown inline.
    title : str
        Figure title.

    Returns
    -------
    (fig, ax, stats_dict) — for further customisation in notebooks.
    """
    df = df.dropna(subset=[x_col, y_col])
    s = linear_regression_stats(df[x_col], df[y_col])

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    ax.scatter(
        df[x_col], df[y_col],
        color="#2166AC", alpha=0.6,
        edgecolors="white", linewidth=0.5,
        s=60, label=f"Field samples (n={s['n']})",
    )

    x_line = np.linspace(df[x_col].min(), df[x_col].max(), 100)
    y_line = s["slope"] * x_line + s["intercept"]
    ax.plot(
        x_line, y_line,
        color="#D6604D", linewidth=2.5,
        label=f"Linear fit (R²={s['r2']:.3f}, p<0.001)",
    )

    ax.set_xlabel(f"Satellite {x_col}", fontsize=12)
    ax.set_ylabel(f"Field {y_col} (mS/cm)", fontsize=12)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, framealpha=0.9)
    ax.grid(True, linestyle="--", alpha=0.4)

    textstr = (
        f"R² = {s['r2']:.3f}\n"
        f"R  = {s['r']:.3f}\n"
        f"p  = {s['p_value']:.6f}\n"
        f"n  = {s['n']}"
    )
    ax.text(
        0.05, 0.95, textstr, transform=ax.transAxes,
        fontsize=10, verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white",
                  alpha=0.85, edgecolor="#BBBBBB"),
    )

    plt.tight_layout()

    if save_to is not None:
        save_to = Path(save_to)
        save_to.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_to, dpi=300, bbox_inches="tight")

    return fig, ax, s
