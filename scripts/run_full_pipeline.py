#!/usr/bin/env python
"""
Full-pipeline CLI reproducer.

Runs every step from the notebooks in sequence and writes the same figures
+ result tables to disk. Intended for one-shot end-to-end reproduction
once the GEE time-series has been cached (notebook 02) at least once.

Usage
-----
    # Full run (will pull GEE time-series if missing — slow):
    python scripts/run_full_pipeline.py

    # Reuse the cached time-series and skip GEE:
    python scripts/run_full_pipeline.py --skip-gee --use-cached

    # Only the cyclone + seasonality + RF + projection chain:
    python scripts/run_full_pipeline.py --skip-validation --skip-gee --use-cached
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure src/ is importable regardless of where the script is invoked from.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import joblib

from src.config import (
    ANALYSIS_START_DATE, ANALYSIS_END_DATE,
    DATA_DIR, FIGURES_DIR, RESULTS_DIR,
    DEFAULT_FIELD_DATA_FILE,
    KFOLD_SPLITS, TEST_SIZE,
    PROJECTION_END_YEAR, STUDY_BBOX,
)


# ─────────────────────────────────────────────────────────────────────
# Step runners
# ─────────────────────────────────────────────────────────────────────
def step_validation() -> None:
    """Notebook 01 equivalent."""
    from src.gee_ndsi import initialize_ee, build_ndsi_collection, sample_points
    from src.validation import load_field_ec, compare_linear_vs_log, plot_validation_scatter
    from datetime import date

    print("\n[1/6] Field validation — NDSI vs EC (n ≈ 162)")
    print("─" * 60)

    ec_path = DATA_DIR / DEFAULT_FIELD_DATA_FILE
    if not ec_path.exists():
        print(f"⚠️  Field EC file not found at {ec_path}. Skipping validation step.")
        return

    initialize_ee()
    df_ec = load_field_ec(ec_path)
    coll = build_ndsi_collection(
        start=date(2024, 2, 1), end=date(2024, 4, 30), platforms=("L8",),
    )
    ts = sample_points(coll, df_ec, scale=30)
    per_point = (
        ts.groupby(["ID", "Latitude", "Longitude"])["ndsi"]
          .mean().reset_index().rename(columns={"ndsi": "NDSI"})
    )
    df_valid = df_ec.merge(per_point[["ID", "NDSI"]], on="ID", how="inner").dropna(
        subset=["NDSI", "EC"]
    )

    stats = compare_linear_vs_log(df_valid)
    print(stats.to_string(index=False))

    plot_validation_scatter(df_valid, save_to=FIGURES_DIR / "fig_validation.png")
    print(f"✓ Saved: figures/fig_validation.png  (n={len(df_valid)})")


def step_gee_time_series(use_cached: bool) -> pd.DataFrame:
    """Notebook 02 equivalent. Returns the regional-mean time-series."""
    from src.gee_ndsi import initialize_ee, build_ndsi_collection, extract_regional_mean
    from src.seasonality import rolling_mean
    from src.visualization import plot_timeseries

    print("\n[2/6] Landsat 5/8/9 NDSI time-series (2000–2026)")
    print("─" * 60)

    cache_path = DATA_DIR / "ndsi_timeseries_2000_2026.csv"

    if use_cached and cache_path.exists():
        ts = pd.read_csv(cache_path, parse_dates=["date"])
        print(f"✓ Loaded cached series ({len(ts)} rows) from {cache_path}")
    else:
        initialize_ee()
        coll = build_ndsi_collection(
            start=ANALYSIS_START_DATE, end=ANALYSIS_END_DATE,
            platforms=("L5", "L8", "L9"),
        )
        n = coll.size().getInfo()
        print(f"GEE collection size: {n} cloud-free scenes")
        ts = extract_regional_mean(coll, scale=30)
        ts.to_csv(cache_path, index=False)
        print(f"✓ Cached {len(ts)} rows → {cache_path}")

    smoothed = rolling_mean(ts, value_col="ndsi_mean", window_months=12)
    plot_timeseries(ts, rolling=smoothed, annotate_cyclones=True,
                    save_to=FIGURES_DIR / "fig_long_timeseries.png")
    print("✓ Saved: figures/fig_long_timeseries.png")
    return ts


def step_cyclone(ts: pd.DataFrame) -> None:
    """Notebook 03 equivalent."""
    from src.cyclone_analysis import analyse_all_events
    from src.visualization import plot_cyclone_effects

    print("\n[3/6] Cyclone-event attribution")
    print("─" * 60)

    results = analyse_all_events(ts)
    print(results.to_string(index=False))
    results.to_csv(RESULTS_DIR / "cyclone_event_attribution.csv", index=False)
    plot_cyclone_effects(results, save_to=FIGURES_DIR / "fig_cyclone_impacts.png")
    print("✓ Saved: results/cyclone_event_attribution.csv, figures/fig_cyclone_impacts.png")


def step_seasonality(ts: pd.DataFrame) -> None:
    """Notebook 04 equivalent."""
    from src.seasonality import monthly_climatology, annual_august_anomaly
    from src.visualization import plot_monthly_climatology, plot_august_anomaly

    print("\n[4/6] Seasonal climatology + August anomaly")
    print("─" * 60)

    clim = monthly_climatology(ts)
    plot_monthly_climatology(clim, save_to=FIGURES_DIR / "fig_monthly_climatology.png")
    print("✓ Saved: figures/fig_monthly_climatology.png")

    aug = annual_august_anomaly(ts)
    aug.to_csv(RESULTS_DIR / "august_anomaly_by_year.csv", index=False)
    plot_august_anomaly(aug, save_to=FIGURES_DIR / "fig_august_anomaly.png")
    print("✓ Saved: figures/fig_august_anomaly.png, results/august_anomaly_by_year.csv")


def step_random_forest(ts: pd.DataFrame):
    """Notebook 05 equivalent. Returns the historical df + fitted model."""
    from src.random_forest import (
        build_feature_matrix, train_rf, kfold_evaluate, feature_importance,
    )
    from src.visualization import plot_feature_importance

    print("\n[5/6] Random Forest training")
    print("─" * 60)

    per_point_path = DATA_DIR / "ndsi_per_point_2000_2026.csv"
    if per_point_path.exists():
        df = pd.read_csv(per_point_path, parse_dates=["date"])
        if "ndsi_mean" in df.columns and "ndsi" not in df.columns:
            df = df.rename(columns={"ndsi_mean": "ndsi"})
        print(f"Loaded per-point training data: {len(df)} rows")
    else:
        df = ts.rename(columns={"ndsi_mean": "ndsi"}).copy()
        df["Latitude"]  = (STUDY_BBOX[1] + STUDY_BBOX[3]) / 2
        df["Longitude"] = (STUDY_BBOX[0] + STUDY_BBOX[2]) / 2
        print("⚠️  Using regional-mean fallback (spatial features will be constant).")

    X, y = build_feature_matrix(df, target_col="ndsi")
    print(f"Feature matrix: {X.shape}")

    kfold = kfold_evaluate(X, y, n_splits=KFOLD_SPLITS)
    print(kfold.to_string(index=False))
    kfold.to_csv(RESULTS_DIR / "rf_kfold_metrics.csv", index=False)

    result = train_rf(X, y, test_size=TEST_SIZE)
    print(f"Test R² = {result.r2_test:.4f} · RMSE = {result.rmse_test:.5f}")
    joblib.dump(result.model, RESULTS_DIR / "rf_ndsi_model.joblib")

    imp = feature_importance(result.model, X.columns)
    plot_feature_importance(imp, save_to=FIGURES_DIR / "fig_feature_importance.png")
    print("✓ Saved: results/rf_ndsi_model.joblib, figures/fig_feature_importance.png")

    return df, result.model


def step_projection(historical: pd.DataFrame, model) -> None:
    """Notebook 06 equivalent."""
    from src.projection import (
        build_future_grid, project, percent_change_summary, identify_hotspots,
    )
    from src.visualization import plot_projection_hotspots

    print("\n[6/6] 2050 projection + hotspot mapping")
    print("─" * 60)

    locations = historical[["Latitude", "Longitude"]].drop_duplicates().reset_index(drop=True)
    future = build_future_grid(locations, start_year=2026, end_year=PROJECTION_END_YEAR)
    print(f"Future grid: {len(future):,} (location × month × year) points")

    proj = project(model, future)
    proj.to_csv(RESULTS_DIR / "projection_2026_2050.csv", index=False)

    summary = percent_change_summary(historical, proj)
    print(summary.to_string(index=False))
    summary.to_csv(RESULTS_DIR / "projection_percent_change_summary.csv", index=False)

    hotspots = identify_hotspots(proj, percentile=90)
    hotspots.to_csv(RESULTS_DIR / "hotspots_top10pct_2050.csv", index=False)
    plot_projection_hotspots(hotspots, save_to=FIGURES_DIR / "fig_2050_hotspots.png")
    print("✓ Saved: figures/fig_2050_hotspots.png, results/projection_*.csv")


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce the full salinity-dynamics pipeline end-to-end."
    )
    parser.add_argument("--skip-validation", action="store_true",
                        help="Skip the field-EC validation step (notebook 01).")
    parser.add_argument("--skip-gee", action="store_true",
                        help="Skip the Google Earth Engine pull. Requires --use-cached.")
    parser.add_argument("--use-cached", action="store_true",
                        help="Reuse the cached time-series CSV if present.")
    args = parser.parse_args()

    print("=" * 60)
    print("SPATIOTEMPORAL SALINITY DYNAMICS — FULL PIPELINE")
    print("=" * 60)

    if not args.skip_validation:
        step_validation()

    if args.skip_gee and not args.use_cached:
        print("\n⚠️  --skip-gee without --use-cached: pipeline cannot continue.")
        return 1

    ts = step_gee_time_series(use_cached=args.use_cached)

    step_cyclone(ts)
    step_seasonality(ts)
    historical, model = step_random_forest(ts)
    step_projection(historical, model)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print(f"Figures:  {FIGURES_DIR}")
    print(f"Results:  {RESULTS_DIR}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
