# Data Sources

This directory holds the raw and intermediate datasets used by the pipeline. **None of these files are tracked in the repository** — they are publicly available (with the exception of the field-EC data) under their original licenses, and the size of the Landsat archive alone would bloat any clone.

Expected layout once everything is in place:

```
data/
├── README.md                              ← this file
├── Soil_Salinity_Data_BD032024.xlsx       ← MIT field-EC dataset (not redistributed)
├── ndsi_timeseries_2000_2026.csv          ← cached output of notebook 02 (regenerable)
├── gadm41_BGD.gpkg                        ← GADM admin boundaries (downloaded once)
└── ibtracs_NI.csv                         ← optional: IBTrACS cyclone tracks
```

## 1. Landsat 5 / 8 / 9 Surface Reflectance — *via Google Earth Engine*

- **What:** Collection-2 Tier-1 Level-2 surface reflectance, atmospherically corrected by USGS.
- **Source:** Streamed from Earth Engine — no local file.
- **Collection IDs:**
  - `LANDSAT/LT05/C02/T1_L2`  (2000 – 2013)
  - `LANDSAT/LC08/C02/T1_L2`  (2013 – )
  - `LANDSAT/LC09/C02/T1_L2`  (2021 – )
- **License:** Public domain (NASA / USGS).
- **Setup:** Free GEE account + `earthengine authenticate` + a project ID configured in `src/config.py` (`GEE_PROJECT_ID`).
- **First use:** Notebook 02 (`02_gee_long_time_series.ipynb`) extracts the regional-mean and per-point NDSI series and **caches the result as `ndsi_timeseries_2000_2026.csv`** so downstream notebooks need not re-run the (~30-minute) GEE pull.

## 2. Field Electrical-Conductivity Dataset — *MIT campaign, March 2024*

- **What:** 162 in-situ EC measurements (mS/cm) with lat / lng / sampling date across the southwest delta. Range 0.05 – 9.08 mS/cm, latitudes 22.22 – 23.14, longitudes 88.91 – 89.64.
- **Source:** Field campaign carried out by an MIT-affiliated team in March 2024 and shared with the authors.
- **License:** **Not redistributed in this repository.** Researchers who need access should contact the data provider; the validation notebook will fail without this file, but every other notebook runs without it.
- **Expected filename:** `Soil_Salinity_Data_BD032024.xlsx`.
- **Loader:** `src.validation.load_field_ec` reads the Excel file with the original two-row header layout.

## 3. GADM v4.1 Administrative Boundaries

- **What:** Admin-2 (district) polygons used to attribute hotspots back to administrative units.
- **Source:** [https://gadm.org/download_country.html](https://gadm.org/download_country.html)
- **Direct URL:** `https://geodata.ucdavis.edu/gadm/gadm4.1/gpkg/gadm41_BGD.gpkg`
- **License:** Free for academic / non-commercial use.
- **Layer used:** `ADM_ADM_2` inside the GeoPackage.

## 4. IBTrACS Cyclone Tracks — *optional*

- **What:** North-Indian-Ocean basin cyclone track records.
- **Source:** NOAA NCEI — [https://www.ncei.noaa.gov/products/international-best-track-archive](https://www.ncei.noaa.gov/products/international-best-track-archive)
- **License:** Public domain.
- **Used by:** The cyclone-attribution step in notebook 03 — although the four headline events (Sidr, Aila, Mahasen, Amphan) are hard-coded in `src/config.CYCLONE_EVENTS`, additional storms can be added by extending that tuple after consulting IBTrACS.

## Coordinate Reference Systems

- Vector layers used for area / distance work → **EPSG:3106** (Gulshan 303 / Bangladesh Transverse Mercator).
- Landsat and GEE outputs → **EPSG:4326** (WGS84 lat/lon).

The codebase reprojects on the fly; configure once in `src/config.py`.

## Reproducibility checklist

Before running any notebook beyond 01, confirm:

1. `earthengine authenticate` has been run on this machine.
2. A `GEE_PROJECT_ID` is set in `src/config.py`.
3. `data/` contains the field EC file *(notebook 01 only)*.
4. Internet access for the initial Landsat / GADM downloads.
