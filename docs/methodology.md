# Extended Methodology

This document fills in detail that the conference paper compresses for length, and is the reference companion to the code in `src/`.

## 1. Why NDSI for soil salinity?

The Normalised Difference Salinity Index,

```
NDSI = (SWIR1 − SWIR2) / (SWIR1 + SWIR2)
```

exploits the differential absorption of soil salts between the two short-wave-infrared windows (~1.6 µm and ~2.2 µm). At low and moderate salt content, SWIR1 reflectance rises faster than SWIR2 as crystalline salt accumulates on the surface, pushing NDSI positive. NDSI has been validated in deltaic contexts comparable to ours — though it does saturate at very high salt loadings, where physically-based indices (e.g. CRSI) outperform it.

For a long-record, multi-sensor reconstruction, NDSI is the right trade-off: it uses two bands present and well-cross-calibrated across Landsat 5 (TM), 8 and 9 (OLI/OLI-2), so the time-series remains comparable across the 2013 Landsat 5 → Landsat 8 transition.

## 2. Cross-sensor harmonisation

Landsat Collection-2 Level-2 SR products are scaled integers; physical reflectance is recovered via

```
ρ = DN × 0.0000275 − 0.2
```

This is applied uniformly across L5/L8/L9 in `src.gee_ndsi._apply_scale_offset`. After scaling, no further cross-sensor bias correction is applied — the NDSI ratio is largely insensitive to multiplicative scaling differences. A more stringent harmonisation step (e.g. the Roy et al. linear transformation) would tighten cross-sensor agreement but is left as future work.

## 3. Cloud handling

Scene-wide cloud cover ≤ 15 % is the primary gate (`MAX_CLOUD_COVER_PCT`). Pixel-level QA-band masking is *not* applied in the published version — for a regional mean over the ~10,000 km² study area, residual cloud pixels average out, and a per-pixel QA pass is the obvious next refinement.

For per-point validation in March 2024 (notebook 01), the small temporal window (Feb – Apr 2024) and tight cloud gate yield consistently clean samples; the 162 paired (NDSI, EC) observations have no rejected scenes.

## 4. Validation design

The validation pairs each field EC measurement with the **time-window-mean NDSI** at the closest Landsat 8 pixel (30 m). The window is the ±60-day envelope around the field-sampling month (Feb–Apr 2024). This pools enough cloud-free scenes for a stable mean while remaining close to the sampling date.

The linear fit attains R² = 0.249; a log–log transformation improves this modestly to R² = 0.273. The improvement is consistent with NDSI's known compressive response at higher salinity values. For the regional-scale projection step, the linear fit is retained — the headline figure of merit is *relative change* over time, not absolute EC translation.

## 5. Random Forest target choice

The Random Forest predicts **NDSI directly**, not EC. Two reasons:

1. The NDSI ↔ EC relationship has scatter (R² = 0.273 log–log) that propagates into any EC-target model, on top of the model's own scatter.
2. The Bangladesh Delta Plan 2100 sets policy targets in salinity *change* not absolute EC; relative projections in NDSI are sufficient and avoid the additional uncertainty layer.

Feature set (`src.random_forest.DEFAULT_FEATURES`):

| Feature | Rationale |
|---|---|
| `year` | Trend signal (post-2000 warming, sea-level rise) |
| `month` | Discrete seasonal cycle |
| `doy` | Smooth seasonal cycle |
| `Latitude` | Spatial gradient (delta interior vs coast) |
| `Longitude` | Spatial gradient (west — Sundarbans — east) |
| `years_since_cyclone` | Post-event recovery lag |
| `month_sin` / `month_cos` | Cyclic encoding so Dec → Jan wraps cleanly |

Hyperparameters in `src.config.RF_DEFAULTS` were selected by light tuning on the 5-fold CV objective; reported test-fold R² ≈ 0.496 and RMSE ≈ 0.00539 (NDSI units).

## 6. Cyclone-event attribution

For each headline cyclone, the change in **regional-mean NDSI** between two 90-day windows (`CYCLONE_WINDOW_DAYS`) — one immediately before, one immediately after landfall — is computed, and a 5,000-iteration non-parametric bootstrap yields a 95 % confidence interval on the difference.

The 90-day choice balances signal (cyclones force surge-driven salinity intrusion that persists weeks to months) against noise (longer windows pick up unrelated seasonal evolution). The CI from the bootstrap is the *only* uncertainty quantification in this step — the data are not iid in time, so parametric tests would be misleading.

## 7. Late-monsoon August anomaly

The dry-season-only paradigm for southwest delta salinity has been the prevailing reading since at least the early 2000s. Our climatology (`src.seasonality.monthly_climatology`) shows a small but persistent secondary peak in August, hypothesised to arise from:

- Mid-monsoon embankment overtopping during peak-discharge events
- Reduced upstream freshwater discharge in the moribund-delta channels
- Capillary rise during brief inter-monsoon dry breaks

The anomaly is robust to (a) sub-setting to single sensors (L5 vs L8/9 separately), and (b) varying the climatology baseline period (2000–2013 vs 2013–2026). It is reported as a hypothesis-generating finding, not a causal attribution.

## 8. Projection assumptions and limits

The 2026 → 2050 roll-forward implicitly assumes:

1. The historical relationships between NDSI and the feature set hold into the future.
2. Cyclone recency is sampled at the historical landfall cadence (~3–5 yr) — the projection grid extrapolates `years_since_cyclone` as a smooth function rather than injecting future stochastic landfalls.
3. No abrupt non-linearities (e.g. catastrophic embankment failure, major coastal-zone-management policy shift) intervene.

These are *strong* assumptions and the published +20.8 % figure should be read as *"continuation of observed climatic regime"* — not a CMIP6-conditioned scenario. Coupling this projection to SSP2-4.5 / SSP5-8.5 CMIP6 downscaled inputs is the natural follow-on, and would be the obvious next manuscript.
