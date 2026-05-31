"""
Landsat NDSI time-series extraction via Google Earth Engine.

NDSI (Normalised Difference Salinity Index) is computed as

    NDSI = (SWIR1 - SWIR2) / (SWIR1 + SWIR2)

using the Landsat Collection-2 Level-2 surface-reflectance products.
Three sensors are stitched: Landsat 5 (2000–2013), Landsat 8 (2013–),
and Landsat 9 (2021–) — see `src.config.LANDSAT_COLLECTIONS`.

The module exposes three layers of API:

- `compute_ndsi_image(image, platform)` — operates on a single ee.Image.
- `build_ndsi_collection(start, end, platforms, region)` — assembles a merged
  multi-sensor NDSI ImageCollection over a date range and region.
- `sample_points(collection, points_df, scale)` — extract per-point NDSI
  time-series and return a pandas DataFrame.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable, Sequence

import pandas as pd

try:
    import ee
except ImportError:  # pragma: no cover - imported lazily so docs / tests work
    ee = None  # type: ignore[assignment]

from src.config import (
    LANDSAT_COLLECTIONS,
    MAX_CLOUD_COVER_PCT,
    SWIR_BANDS,
    SR_SCALE,
    SR_OFFSET,
    STUDY_BBOX,
    GEE_PROJECT_ID,
)


def initialize_ee(project_id: str | None = None) -> None:
    """
    Initialize the Earth Engine client.

    Authenticate locally once with ``earthengine authenticate`` then call
    this from every entry-point notebook / script.
    """
    if ee is None:
        raise ImportError(
            "earthengine-api is not installed. "
            "Install with: pip install earthengine-api"
        )
    project = project_id or GEE_PROJECT_ID
    if project is None:
        raise ValueError(
            "No Earth Engine project ID configured. "
            "Set GEE_PROJECT_ID in src/config.py or pass project_id explicitly."
        )
    ee.Initialize(project=project)


def _apply_scale_offset(image, platform: str):
    """Scale Landsat Collection-2 SR bands to physical reflectance [0, 1]."""
    swir1_band, swir2_band = SWIR_BANDS[platform]
    swir1 = image.select(swir1_band).multiply(SR_SCALE).add(SR_OFFSET)
    swir2 = image.select(swir2_band).multiply(SR_SCALE).add(SR_OFFSET)
    return swir1.rename("SWIR1"), swir2.rename("SWIR2")


def compute_ndsi_image(image, platform: str):
    """
    Compute NDSI as a new band on a single Landsat image.

    Parameters
    ----------
    image : ee.Image
        Single Landsat Collection-2 L2 surface-reflectance image.
    platform : {"L5", "L8", "L9"}
        Which sensor — controls the SWIR band names.

    Returns
    -------
    ee.Image with an added `NDSI` band and the original metadata preserved.
    """
    if platform not in SWIR_BANDS:
        raise ValueError(f"Unknown platform {platform!r}. Choose from {list(SWIR_BANDS)}.")

    swir1, swir2 = _apply_scale_offset(image, platform)
    ndsi = swir1.subtract(swir2).divide(swir1.add(swir2)).rename("NDSI")
    return image.addBands(ndsi)


def _build_single_collection(
    platform: str,
    start: date,
    end: date,
    region,
    max_cloud: float,
):
    """Build a per-platform NDSI ImageCollection."""
    coll = (
        ee.ImageCollection(LANDSAT_COLLECTIONS[platform])
          .filterDate(str(start), str(end))
          .filterBounds(region)
          .filter(ee.Filter.lt("CLOUD_COVER", max_cloud))
          .map(lambda img: compute_ndsi_image(img, platform))
          .select(["NDSI"])
    )
    return coll


def build_ndsi_collection(
    start: date,
    end: date,
    platforms: Sequence[str] = ("L5", "L8", "L9"),
    region: "ee.Geometry | None" = None,
    max_cloud: float = MAX_CLOUD_COVER_PCT,
):
    """
    Build a merged NDSI ImageCollection across one or more sensors.

    Parameters
    ----------
    start, end : datetime.date
        Inclusive start, exclusive end of the analysis window.
    platforms : sequence of {"L5", "L8", "L9"}
        Which Landsat platforms to merge. Order does not matter.
    region : ee.Geometry, optional
        Geographic filter. Defaults to the configured study bounding box.
    max_cloud : float
        Maximum scene-wide cloud cover (%).

    Returns
    -------
    ee.ImageCollection of single-band NDSI images, sorted by acquisition time.
    """
    if ee is None:
        raise ImportError("earthengine-api is not installed.")

    if region is None:
        region = ee.Geometry.Rectangle(list(STUDY_BBOX))

    collections = [
        _build_single_collection(p, start, end, region, max_cloud) for p in platforms
    ]
    merged = collections[0]
    for c in collections[1:]:
        merged = merged.merge(c)
    return merged.sort("system:time_start")


def sample_points(
    collection,
    points: pd.DataFrame,
    scale: float = 30,
    lat_col: str = "Latitude",
    lng_col: str = "Longitude",
) -> pd.DataFrame:
    """
    Extract per-point NDSI time-series from a GEE collection.

    For each (lat, lng) row in ``points``, samples NDSI at every image in
    the collection and returns a long-format DataFrame with one row per
    (point, image-date) pair.

    Parameters
    ----------
    collection : ee.ImageCollection
        Output of `build_ndsi_collection`.
    points : pandas.DataFrame
        Must contain ``lat_col`` and ``lng_col`` columns. Other columns are
        carried through to the output.
    scale : float
        Native resolution at which to sample (30 m for Landsat).
    lat_col, lng_col : str
        Column names holding latitudes / longitudes in WGS84 degrees.

    Returns
    -------
    DataFrame with columns: original point columns + `date`, `ndsi`.

    Notes
    -----
    This issues one server call per point; for very large point sets,
    rewrite to use `ee.FeatureCollection` + `reduceRegions`.
    """
    if ee is None:
        raise ImportError("earthengine-api is not installed.")

    records: list[dict] = []
    for _, row in points.iterrows():
        pt = ee.Geometry.Point([row[lng_col], row[lat_col]])

        def _reduce(img):
            value = img.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=pt,
                scale=scale,
                maxPixels=1e9,
            ).get("NDSI")
            return ee.Feature(None, {
                "ndsi": value,
                "date": img.date().format("YYYY-MM-dd"),
            })

        feats = collection.map(_reduce).filter(ee.Filter.notNull(["ndsi"]))
        ts = feats.getInfo()["features"]

        base = {k: row[k] for k in points.columns}
        for f in ts:
            rec = dict(base)
            rec["date"] = f["properties"]["date"]
            rec["ndsi"] = f["properties"]["ndsi"]
            records.append(rec)

    out = pd.DataFrame.from_records(records)
    if not out.empty:
        out["date"] = pd.to_datetime(out["date"])
    return out


def extract_regional_mean(
    collection,
    region=None,
    scale: float = 30,
) -> pd.DataFrame:
    """
    Reduce every image in the collection to a single scalar regional mean.

    This is the cheap-and-fast alternative to per-point sampling when you
    only need an area-averaged time-series (e.g. for plotting the long-term
    trend over the study domain).

    Parameters
    ----------
    collection : ee.ImageCollection
    region : ee.Geometry, optional
        Defaults to the configured study bounding box.
    scale : float
        Spatial scale (m) at which to reduce.

    Returns
    -------
    DataFrame with columns: `date`, `ndsi_mean`.
    """
    if ee is None:
        raise ImportError("earthengine-api is not installed.")

    if region is None:
        region = ee.Geometry.Rectangle(list(STUDY_BBOX))

    def _reduce(img):
        m = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=scale,
            maxPixels=1e10,
        ).get("NDSI")
        return ee.Feature(None, {
            "ndsi_mean": m,
            "date": img.date().format("YYYY-MM-dd"),
        })

    feats = collection.map(_reduce).filter(ee.Filter.notNull(["ndsi_mean"]))
    rows = feats.getInfo()["features"]
    df = pd.DataFrame([
        {"date": pd.to_datetime(f["properties"]["date"]),
         "ndsi_mean": f["properties"]["ndsi_mean"]}
        for f in rows
    ])
    return df.sort_values("date").reset_index(drop=True)
