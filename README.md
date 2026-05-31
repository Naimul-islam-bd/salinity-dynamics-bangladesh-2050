# Spatiotemporal Salinity Dynamics in Southwest Bangladesh (2000–2050)

**Cyclone Impacts, Seasonal Anomalies, and Random Forest Projections for Delta Governance**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Manuscript: Under Review](https://img.shields.io/badge/manuscript-under%20review-orange)]()
[![Conference: ICSD 2026](https://img.shields.io/badge/conference-ICSD%202026-blueviolet)]()
[![Data: Google Earth Engine](https://img.shields.io/badge/data-Google%20Earth%20Engine-4285F4)](https://earthengine.google.com)

---

## Overview

This repository implements the analysis pipeline behind the conference manuscript:

> Islam, N., & Ahmed, N. (2026). *Spatiotemporal Salinity Dynamics in Southwest Bangladesh (2000–2026): Cyclone Impacts, Seasonal Anomalies, and Random Forest Projections for Delta Governance*. **Under review — 8th International Conference on Sustainable Development (ICSD 2026), Dhaka.**

The study reconstructs a **26-year, high-cadence record of surface soil salinity** across the salinity-vulnerable districts of southwest Bangladesh — **Khulna**, **Satkhira**, and **Bagerhat** — and uses it to (a) attribute observed change to cyclone landfalls and seasonal forcing, (b) train a Random Forest projector calibrated against field electrical-conductivity measurements, and (c) project salinity through 2050 under a continuation of the observed climatic regime.

## Key Findings

| Finding | Magnitude |
|---|---|
| Cloud-free Landsat observations assembled (2000 – 2026) | **667** scenes (L5 + L8/9 via GEE) |
| Field-validation pairs (NDSI vs EC, March 2024) | **n = 162**, p < 0.001 |
| Random Forest projection skill | **R² = 0.496**, **RMSE = 0.00539** (NDSI units) |
| Projected salinity increase by 2050 (study domain mean) | **+20.8 %** |
| Novel finding: late-monsoon salinity peak in moribund delta | **August anomaly** challenges the dry-season-only paradigm |

These results align with — and refine — the planning horizon set out in the **Bangladesh Delta Plan 2100**, by giving sub-district-resolved salinity expectations rather than national averages.

## Methodology — at a glance

```
┌──────────────────────────────────────────────────────────────────────┐
│  STEP 1 · TIME-SERIES ASSEMBLY  (Google Earth Engine)                │
│    Landsat 5 (2000–2013) + Landsat 8/9 (2013–2026)                   │
│    Cloud-mask → compute NDSI = (SWIR1 − SWIR2) / (SWIR1 + SWIR2)     │
│    Reduce to monthly means × study-area pixel grid                   │
├──────────────────────────────────────────────────────────────────────┤
│  STEP 2 · FIELD VALIDATION                                           │
│    162 EC measurements (March 2024) ↔ co-located NDSI samples        │
│    Linear & log-transform regression, scatter + residual diagnostics │
├──────────────────────────────────────────────────────────────────────┤
│  STEP 3 · CYCLONE-EVENT ATTRIBUTION                                  │
│    Compare pre- vs post-landfall NDSI for Sidr (2007), Aila (2009),  │
│    Mahasen (2013), Amphan (2020); difference-of-means + bootstrap CI │
├──────────────────────────────────────────────────────────────────────┤
│  STEP 4 · SEASONAL ANOMALY DETECTION                                 │
│    Monthly climatology vs running mean → August anomaly surfaces     │
├──────────────────────────────────────────────────────────────────────┤
│  STEP 5 · RANDOM-FOREST PROJECTION                                   │
│    Features: month, year-trend, lat, lng, cyclone-recency, season    │
│    Target  : NDSI (continuous) — RandomForestRegressor               │
│    Validate: k-fold + held-out validation → R² ≈ 0.496               │
├──────────────────────────────────────────────────────────────────────┤
│  STEP 6 · 2050 SCENARIO PROJECTION                                   │
│    Roll features forward (2026 → 2050), predict per-pixel NDSI       │
│    Aggregate to district / upazila → +20.8 % domain-mean increase    │
└──────────────────────────────────────────────────────────────────────┘
```

## Repository Structure

```
salinity-dynamics-bangladesh-2050/
├── README.md                          ← you are here
├── LICENSE                            ← MIT
├── CITATION.cff                       ← machine-readable citation
├── requirements.txt                   ← pip dependencies
├── environment.yml                    ← conda alternative
├── .gitignore
│
├── src/                               ← reusable Python package
│   ├── __init__.py
│   ├── config.py                      ← study area, CRS, cyclones, paths
│   ├── gee_ndsi.py                    ← Landsat 5/8/9 NDSI time-series via GEE
│   ├── validation.py                  ← field-EC ↔ satellite-NDSI validation
│   ├── cyclone_analysis.py            ← pre/post landfall windows + bootstrap
│   ├── seasonality.py                 ← monthly climatology, August anomaly
│   ├── random_forest.py               ← RF training, k-fold, feature importance
│   ├── projection.py                  ← roll-forward to 2050, scenario logic
│   └── visualization.py               ← time-series, hotspot maps, anomaly viz
│
├── notebooks/                         ← step-by-step research walk-through
│   ├── 01_validation_ndsi_vs_ec.ipynb     ← n=162, R² and log-R² (March 2024)
│   ├── 02_gee_long_time_series.ipynb      ← 26-year Landsat extraction
│   ├── 03_cyclone_event_analysis.ipynb    ← Sidr, Aila, Mahasen, Amphan
│   ├── 04_seasonal_anomaly.ipynb          ← August anomaly discovery
│   ├── 05_random_forest_training.ipynb    ← model fit + diagnostics
│   └── 06_2050_projection.ipynb           ← future scenario + hotspot maps
│
├── scripts/
│   └── run_full_pipeline.py           ← CLI: reproduce all figures end-to-end
│
├── data/                              ← raw + intermediate (not tracked; see data/README.md)
├── figures/                           ← generated plots
├── results/                           ← CSV exports of summary tables
└── docs/
    ├── methodology.md                 ← extended methodology notes
    └── cyclone_events.md              ← per-storm landfall metadata
```

## Installation

```bash
# Clone
git clone https://github.com/Naimul-islam-bd/salinity-dynamics-bangladesh-2050.git
cd salinity-dynamics-bangladesh-2050

# Option A — pip
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Option B — conda
conda env create -f environment.yml
conda activate salinity-2050
```

### Google Earth Engine authentication

The time-series extraction step requires a free Google Earth Engine account.
After `pip install earthengine-api`, authenticate once per machine:

```bash
earthengine authenticate
```

then set your project in `src/config.py` (`GEE_PROJECT_ID`).

## Reproducing the Paper

### Notebook walk-through (recommended)

```bash
jupyter lab notebooks/
```

Run the six notebooks in order. Each is self-contained, prints intermediate diagnostics, and writes outputs to `figures/` or `results/`.

| Notebook | Output |
|---|---|
| `01_validation_ndsi_vs_ec.ipynb` | `figures/fig_validation.png`, summary stats |
| `02_gee_long_time_series.ipynb` | `data/ndsi_timeseries_2000_2026.csv` |
| `03_cyclone_event_analysis.ipynb` | `figures/fig_cyclone_impacts.png`, per-storm effect sizes |
| `04_seasonal_anomaly.ipynb` | `figures/fig_august_anomaly.png` |
| `05_random_forest_training.ipynb` | `results/rf_metrics.csv`, feature importance plot |
| `06_2050_projection.ipynb` | `figures/fig_2050_hotspots.png`, district projection table |

### One-shot reproduction

```bash
python scripts/run_full_pipeline.py --skip-gee --use-cached
```

(GEE extraction takes ~30 minutes; `--use-cached` reads the pre-exported CSV if you've run notebook 02 once already.)

## Data Sources

All datasets are public; **none are tracked in the repository**. See [`data/README.md`](data/README.md) for download links, license terms, and the expected file layout.

| Dataset | Source | License |
|---|---|---|
| Landsat 5 SR Tier 1 (`LANDSAT/LT05/C02/T1_L2`) | USGS / Google Earth Engine | Public domain |
| Landsat 8 SR Tier 1 (`LANDSAT/LC08/C02/T1_L2`) | USGS / Google Earth Engine | Public domain |
| Landsat 9 SR Tier 1 (`LANDSAT/LC09/C02/T1_L2`) | USGS / Google Earth Engine | Public domain |
| Field EC measurements (n=162, March 2024) | MIT field campaign — requires permission for redistribution | Contact data provider |
| Cyclone tracks (IBTrACS v04r00, NI basin) | NOAA NCEI | Public domain |
| Administrative boundaries (GADM v4.1) | [gadm.org](https://gadm.org) | Academic / non-commercial |

## Study Area

Three contiguous southwestern districts most exposed to salinity intrusion in the lower Ganges delta:

| District | Approx. study coverage |
|---|---|
| Khulna | Greater Khulna upazilas + coastal Sundarbans buffer |
| Satkhira | Whole district, including southern Shyamnagar |
| Bagerhat | Coastal upazilas (Mongla, Sarankhola, Morrelganj) |

Bounding box (approx.): `22.0°N – 23.5°N` × `88.8°E – 89.8°E`.

## Citation

If you use this code or methodology, please cite:

```bibtex
@unpublished{islam2026salinity,
  author    = {Islam, Naimul and Ahmed, Niloy},
  title     = {Spatiotemporal Salinity Dynamics in Southwest Bangladesh (2000--2026):
               Cyclone Impacts, Seasonal Anomalies, and Random Forest Projections
               for Delta Governance},
  year      = {2026},
  note      = {Submitted to the 8th International Conference on Sustainable
               Development (ICSD 2026), Dhaka, 30--31 March 2026 — under review}
}
```

A machine-readable `CITATION.cff` is provided.

## Author

**Naimul Islam**
Civil Engineer · Water Resources & WASH · Climate-Resilient Infrastructure Research
Dhaka, Bangladesh
[LinkedIn](https://linkedin.com/in/naimul-islam-bd) · naimul.islam.bangladesh@gmail.com

## Acknowledgments

Field salinity measurements collected and shared by a March 2024 MIT-affiliated soil-salinity field campaign in southwest Bangladesh — gratefully acknowledged. Landsat archive courtesy of USGS / NASA, accessed via Google Earth Engine. IBTrACS cyclone-track archive courtesy of NOAA NCEI. Administrative boundary polygons via GADM. This pipeline was developed independently as part of an active research portfolio on climate-resilient infrastructure in deltaic and coastal-vulnerable contexts.

## License

Code released under the [MIT License](LICENSE). Each dataset retains its original license — see the data sources table above.
