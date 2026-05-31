"""
Spatiotemporal Salinity Dynamics in Southwest Bangladesh (2000–2050)
=====================================================================

Reproducible analysis pipeline for the ICSD 2026 manuscript.

Author : Naimul Islam <naimul.islam.bangladesh@gmail.com>
License: MIT
"""
from src.config import (
    BD_CRS,
    GEOGRAPHIC_CRS,
    DATA_DIR,
    FIGURES_DIR,
    RESULTS_DIR,
    STUDY_DISTRICTS,
    STUDY_BBOX,
    ANALYSIS_START_DATE,
    ANALYSIS_END_DATE,
    CYCLONE_EVENTS,
    CYCLONE_WINDOW_DAYS,
    PROJECTION_END_YEAR,
    RF_DEFAULTS,
)
from src.gee_ndsi import (
    initialize_ee,
    compute_ndsi_image,
    build_ndsi_collection,
    sample_points,
    extract_regional_mean,
)
from src.validation import (
    load_field_ec,
    linear_regression_stats,
    compare_linear_vs_log,
    plot_validation_scatter,
)
from src.cyclone_analysis import (
    bootstrap_diff_ci,
    analyse_event,
    analyse_all_events,
    years_since_last_cyclone,
)
from src.seasonality import (
    add_temporal_features,
    monthly_climatology,
    deseasonalise,
    annual_august_anomaly,
    rolling_mean,
)
from src.random_forest import (
    build_feature_matrix,
    train_rf,
    kfold_evaluate,
    feature_importance,
    TrainResult,
    DEFAULT_FEATURES,
)
from src.projection import (
    build_future_grid,
    project,
    percent_change_summary,
    identify_hotspots,
)
from src.visualization import (
    plot_timeseries,
    plot_monthly_climatology,
    plot_cyclone_effects,
    plot_feature_importance,
    plot_projection_hotspots,
    plot_august_anomaly,
    PALETTE,
)

__version__ = "0.1.0"
__author__ = "Naimul Islam"
