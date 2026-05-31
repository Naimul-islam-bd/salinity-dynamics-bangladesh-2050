# Cyclone Events Reference

Per-storm metadata for the four headline cyclones used in the attribution analysis (`src.config.CYCLONE_EVENTS`). All landfall dates are the operational BMD / IMD reported values; this file is the human-readable companion to the hard-coded `CycloneEvent` tuples.

Adding a storm? Add a new `CycloneEvent(...)` entry in `src/config.py` AND a new section here.

---

## Sidr — 15 November 2007

- **Category at landfall:** Category 4 equivalent.
- **Landfall location:** Eastern Sundarbans / Barguna coast.
- **Season:** Post-monsoon.
- **Why it matters:** Devastating storm surge into Bagerhat, Barguna, and southern Patuakhali. Mass embankment damage caused multi-week saline ingress and shifted the salinity baseline in coastal Bagerhat for several seasons. Reported death toll ~3,400.
- **NDSI signal expected:** Sharp post-landfall rise, slow recovery over 4–6 months.

## Aila — 25 May 2009

- **Category at landfall:** Category 1 cyclone, but exceptionally damaging surge.
- **Landfall location:** Sundarbans coast straddling the Bangladesh – West Bengal border.
- **Season:** Pre-monsoon (immediately preceding the SW monsoon onset).
- **Why it matters:** This is the canonical case study for multi-year salinity persistence in Bangladesh. Hundreds of kilometres of coastal embankments were breached in Satkhira; some breaches remained unrepaired for >2 years, during which the trapped saline water salinised inland soils that had previously been considered freshwater. The case is what motivated the Bangladesh Delta Plan 2100's coastal-zone chapter.
- **NDSI signal expected:** Pronounced post-landfall rise persisting >12 months in Satkhira.

## Mahasen — 16 May 2013

- **Category at landfall:** Category 1.
- **Landfall location:** Chittagong / Noakhali coast.
- **Season:** Pre-monsoon.
- **Why it matters:** Weaker than Sidr or Aila, but useful as a control: a coastal cyclone whose track passes east of the southwest delta. Expected NDSI signal in the SW study area should be muted, providing a null-comparison case.
- **NDSI signal expected:** Small / negligible post-landfall change in Khulna–Satkhira–Bagerhat.

## Amphan — 20 May 2020

- **Category at landfall:** Category 5 super cyclone, weakened to Cat 2-equivalent at landfall.
- **Landfall location:** Sundarbans / West Bengal coast, immediately west of the Bangladesh study area.
- **Season:** Pre-monsoon (also COVID-19 evacuation-constrained).
- **Why it matters:** First super cyclone in the Bay of Bengal in 20 years; substantial surge into Satkhira and Khulna. Embankment failures of varying severity; recovery in some areas was confounded by pandemic-era logistics.
- **NDSI signal expected:** Strong post-landfall rise in Satkhira, with measurable signal in Khulna; recovery time intermediate between Sidr and Aila.

---

## What's deliberately *not* in this list

- **Roanu (2016)**, **Mora (2017)**, **Fani (2019)**, **Bulbul (2019)**, **Yaas (2021)**, **Sitrang (2022)**, **Mocha (2023)**, **Remal (2024)** — all relevant cyclones, but either too far east of the study area, or sufficiently weaker, that the per-storm signal-to-noise ratio is low. They can be added to `CYCLONE_EVENTS` if a follow-on study targets a wider basin or finer effect detection.

- **Cyclones before 2000** (e.g. 1991, 1997) — outside the Landsat 5 collection window used here.
