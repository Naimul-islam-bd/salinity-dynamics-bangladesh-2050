"""
Configuration constants for the salinity-dynamics analysis.

All study-area definitions, cyclone-event windows, default file paths,
and modelling thresholds live here so that the rest of the package
contains no hard-coded magic numbers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# Project paths
# ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
FIGURES_DIR = PROJECT_ROOT / "figures"
RESULTS_DIR = PROJECT_ROOT / "results"

# Create output directories on import (idempotent)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
# Google Earth Engine
# ─────────────────────────────────────────────────────────────────────
# Replace with your own Earth Engine project ID (from console.cloud.google.com).
# Authenticate locally with `earthengine authenticate` before running notebook 02.
GEE_PROJECT_ID: str | None = None  # e.g. "research-paper-465104"

# Earth Engine Landsat surface-reflectance collection IDs (Collection 2, Tier 1).
LANDSAT_COLLECTIONS = {
    "L5": "LANDSAT/LT05/C02/T1_L2",  # active ~ 1984 – 2013
    "L8": "LANDSAT/LC08/C02/T1_L2",  # active 2013 –
    "L9": "LANDSAT/LC09/C02/T1_L2",  # active 2021 –
}

# Maximum acceptable scene-wide cloud cover (%) for the time-series extraction.
# Tightening this drops some scenes; loosening admits more noise. 15 is a
# common compromise for delta-scale work where complete cloud-free coverage
# is hard to achieve, especially during the monsoon.
MAX_CLOUD_COVER_PCT = 15

# SWIR band identifiers per platform (used for NDSI calculation).
# Landsat 5 numbering differs from 8/9; both pairs map to ~1.6 µm and ~2.2 µm.
SWIR_BANDS = {
    "L5": ("SR_B5", "SR_B7"),  # TM:  SWIR1, SWIR2
    "L8": ("SR_B6", "SR_B7"),  # OLI: SWIR1, SWIR2
    "L9": ("SR_B6", "SR_B7"),  # OLI: SWIR1, SWIR2
}

# Per-platform surface-reflectance scale factor and offset
# (Collection 2 SR_B* values are scaled integers — see USGS Landsat docs).
SR_SCALE = 0.0000275
SR_OFFSET = -0.2

# ─────────────────────────────────────────────────────────────────────
# Study area — southwest Bangladesh
# ─────────────────────────────────────────────────────────────────────
STUDY_DISTRICTS = ["Khulna", "Satkhira", "Bagerhat"]

# Bounding-box for GEE region-of-interest (W, S, E, N) — covers all three
# districts plus a small coastal buffer into the Sundarbans.
STUDY_BBOX = (88.80, 22.00, 89.80, 23.50)

# Time-series window
ANALYSIS_START_DATE = date(2000, 1, 1)
ANALYSIS_END_DATE = date(2026, 12, 31)

# CRS used for all area / distance calculations.
BD_CRS = "EPSG:3106"        # Gulshan 303 / Bangladesh Transverse Mercator
GEOGRAPHIC_CRS = "EPSG:4326"  # WGS84 lat/lon (used by GEE natively)

# ─────────────────────────────────────────────────────────────────────
# Cyclone events of interest
# ─────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class CycloneEvent:
    """A single historical cyclone affecting the study area."""
    name: str
    landfall_date: date
    season: str               # "pre-monsoon" / "monsoon" / "post-monsoon"
    notes: str

# Major cyclones with documented salinity impacts in the southwest delta.
# Landfall dates are the BMD / IMD operationally reported values.
CYCLONE_EVENTS: tuple[CycloneEvent, ...] = (
    CycloneEvent("Sidr",     date(2007, 11, 15), "post-monsoon",
                 "Cat 4 at landfall — devastating impact on Bagerhat, Patuakhali"),
    CycloneEvent("Aila",     date(2009,  5, 25), "pre-monsoon",
                 "Embankment breaches caused multi-year salinity persistence in Satkhira"),
    CycloneEvent("Mahasen",  date(2013,  5, 16), "pre-monsoon",
                 "Cat 1 — coastal Bagerhat flooding"),
    CycloneEvent("Amphan",   date(2020,  5, 20), "pre-monsoon",
                 "Super cyclone — surge intrusion into Satkhira, Khulna"),
)

# Window (days) before/after landfall used for pre vs post NDSI comparison
# in the cyclone-attribution step. 90 days = roughly one season.
CYCLONE_WINDOW_DAYS = 90

# ─────────────────────────────────────────────────────────────────────
# Random Forest model defaults
# ─────────────────────────────────────────────────────────────────────
RF_DEFAULTS = {
    "n_estimators": 500,
    "max_depth": 14,
    "min_samples_leaf": 4,
    "random_state": 42,
    "n_jobs": -1,
}

# k-fold cross-validation splits
KFOLD_SPLITS = 5

# Train/test split fraction (held-out test set)
TEST_SIZE = 0.20

# ─────────────────────────────────────────────────────────────────────
# Projection horizon
# ─────────────────────────────────────────────────────────────────────
PROJECTION_END_YEAR = 2050

# Validation file (MIT field campaign — see data/README.md).
# Filename is the user-supplied default; override at call site if needed.
DEFAULT_FIELD_DATA_FILE = "Soil_Salinity_Data_BD032024.xlsx"
