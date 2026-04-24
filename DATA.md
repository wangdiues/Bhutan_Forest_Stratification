# Data Description

**Study:** Integrating biodiversity, structural complexity, and canopy dynamics across a national forest gradient in Bhutan: Implications for monitoring and management
**Authors:** Wangdi, Laxmi Sagar, Sangay Chedup, Sangay Dorjee, Tashi Waiba Norbu
**Journal:** Forest Ecology and Management (submitted 2026)

---

## Overview

This study integrates three independent data streams — field-based vegetation inventories, gridded environmental rasters, and MODIS satellite time series — to quantify forest biodiversity, structural complexity, and canopy greenness trends across Bhutan's full elevational gradient (113–5,469 m a.s.l.).

---

## 1. Bhutan National Forest Inventory (NFI)

| Attribute | Value |
|-----------|-------|
| **Source** | Department of Forests and Park Services, Ministry of Energy and Natural Resources, Royal Government of Bhutan |
| **Citation** | NFI (2022) |
| **Spatial extent** | Bhutan-wide (88.7°–92.2°E, 26.7°–28.4°N) |
| **Number of plots** | 1,942 georeferenced plots |
| **Raw records** | 107,917 |
| **Cleaned records** | 107,876 |
| **Unique species** | 2,185 standardized species names |
| **Elevation range** | 113–5,469 m a.s.l. (mean 2,454.08 ± 1,271.20 m) |
| **CRS** | EPSG:4326 (WGS 84) |

### 1.1 Vegetation Strata

Records are stratified across three vertical vegetation layers:

| Stratum | Mean plot richness (±SD) | Abundance treatment |
|---------|--------------------------|---------------------|
| Trees | 9.14 ± 7.31 | Presence-only (count = 1 per occurrence) |
| Shrubs | 5.51 ± 4.20 | Numeric abundance where recorded |
| Herbs | 2.80 ± 3.17 | Presence-only (count = 1 per occurrence) |

> **Note:** Non-null abundance values occurred only in shrub records. Tree and herb records contribute a single count per plot–species occurrence. This differential treatment may introduce bias in abundance-sensitive metrics such as Bray–Curtis dissimilarity.

### 1.2 Plot-level Fields

| Field | Description |
|-------|-------------|
| `plot_id` | Unique plot identifier |
| `longitude` | Decimal degrees (EPSG:4326) |
| `latitude` | Decimal degrees (EPSG:4326) |
| `species_name` | Standardized scientific species name |
| `local_name` | Vernacular/local species name |
| `stratum_count` | Abundance value (shrubs only; else 1) |

### 1.3 Forest-Type Classes (12 classes)

| Forest Type | *n* plots | Mean richness ± SD |
|-------------|----------|--------------------|
| Subtropical Forest | 163 | 26.01 ± 8.70 |
| Warm Broadleaved Forest | 376 | 24.23 ± 8.54 |
| Cool Broadleaved Forest | 301 | 18.55 ± 7.39 |
| Spruce Forest† | 21 | 17.76 ± 5.05 |
| Evergreen Oak Forest | 179 | 17.27 ± 6.47 |
| Hemlock Forest | 105 | 16.04 ± 6.28 |
| Blue Pine Forest | 54 | 15.67 ± 5.18 |
| Chirpine Forest | 55 | 11.58 ± 7.13 |
| Fir Forest | 206 | 11.33 ± 5.16 |
| Non-Forest | 389 | 11.25 ± 7.49 |
| Juniper Rhododendron Scrub | 57 | 10.70 ± 5.38 |
| Dry Alpine Scrub | 36 | 8.19 ± 4.74 |
| **Total** | **1,942** | **17.09 ± 9.13** |

†Forest types with *n* < 30 carry elevated uncertainty in SCI estimates.

### 1.4 Species Richness by Elevation Band

| Elevation band (m) | *n* plots | Mean richness | SD | Median |
|--------------------|----------|---------------|----|--------|
| <500 | 102 | 22.92 | 10.41 | 22.0 |
| 500–1,000 | 172 | 24.83 | 8.90 | 26.0 |
| 1,000–1,500 | 249 | 21.04 | 9.53 | 21.0 |
| 1,500–2,000 | 255 | 21.57 | 9.33 | 21.0 |
| 2,000–2,500 | 257 | 17.59 | 7.16 | 18.0 |
| 2,500–3,000 | 253 | 16.01 | 6.00 | 15.0 |
| 3,000–3,500 | 205 | 14.24 | 5.57 | 13.0 |
| 3,500–4,000 | 164 | 11.10 | 5.75 | 10.0 |
| >4,000 | 285 | 8.86 | 5.59 | 8.0 |

### 1.5 Data Cleaning

Cleaning was performed using `pandas` (McKinney, 2010):
- Records concatenated into a unified long-format table
- Column names standardized; leading/trailing whitespace removed
- Species-name strings cleaned for consistency
- Geographic coordinates parsed and validated against Bhutan national bounds
- Records with missing plot identifiers or species names excluded
- 41 records removed (107,917 raw → 107,876 cleaned)
- Taxonomic duplicate-candidate report generated; synonym resolution **not** applied automatically to avoid unverified taxonomic assumptions
- Explicit height thresholds for vertical strata were not recorded in field protocols; strata treated operationally per NFI classification (Trees, Shrubs, Herbs)

---

## 2. Environmental Raster Data

All environmental variables were extracted at plot centroids using point sampling of raster cell values via `rasterio` (Bunt et al., 2026). The final environmental dataset comprised **1,942 plots** with **24 numeric variables** (3 plots had missing values for bioclimatic variables).

### 2.1 Digital Elevation Model (DEM)

| Attribute | Value |
|-----------|-------|
| **Variables extracted** | Elevation (m a.s.l.), slope (°), aspect |
| **Terrain derivatives** | Slope and aspect computed using 3 × 3 moving windows |
| **Aspect decomposition** | Northness = sin(aspect); Eastness = cos(aspect) |

### 2.2 Bioclimatic Variables (WorldClim/CMIP6)

| Attribute | Value |
|-----------|-------|
| **Source** | High-resolution (250 m) CMIP6 climate grids for Bhutan |
| **Citation** | Dorji et al. (2025) |
| **Variables** | bio1–bio19 (19 standard bioclimatic variables) |
| **Resolution** | 250 m |

**Summary statistics across 1,942 NFI plots:**

| Variable | Description | Mean | SD | Min | Max |
|----------|-------------|------|----|-----|-----|
| bio1 | Annual mean temperature (°C) | 12.34 | 6.37 | −4.31 | 23.79 |
| bio2 | Mean diurnal range (°C) | 8.40 | 1.26 | 5.66 | 13.16 |
| bio3 | Isothermality (%) | 42.02 | 2.98 | 32.71 | 50.19 |
| bio4 | Temperature seasonality (SD × 100) | 430.57 | 52.65 | 330.33 | 643.00 |
| bio5 | Max temperature warmest month (°C) | 21.04 | 5.76 | 6.70 | 31.70 |
| bio6 | Min temperature coldest month (°C) | 1.09 | 7.16 | −17.40 | 12.90 |
| bio7 | Temperature annual range (°C) | 19.95 | 2.31 | 15.30 | 28.10 |
| bio8 | Mean temperature wettest quarter (°C) | 17.17 | 5.70 | 3.08 | 27.47 |
| bio9 | Mean temperature driest quarter (°C) | 7.65 | 6.66 | −9.95 | 19.78 |
| bio10 | Mean temperature warmest quarter (°C) | 17.20 | 5.69 | 3.08 | 27.47 |
| bio11 | Mean temperature coldest quarter (°C) | 6.69 | 6.67 | −11.27 | 18.78 |
| bio12 | Annual precipitation (mm) | 1719.85 | 866.57 | 548.20 | 5202.60 |
| bio13 | Precipitation wettest month (mm) | 409.47 | 225.13 | 126.80 | 1317.80 |
| bio14 | Precipitation driest month (mm) | 5.62 | 3.93 | 0.80 | 20.20 |
| bio15 | Precipitation seasonality (CV) | 94.57 | 6.39 | 77.00 | 113.63 |
| bio16 | Precipitation wettest quarter (mm) | 1017.70 | 565.66 | 286.40 | 3448.60 |
| bio17 | Precipitation driest quarter (mm) | 26.40 | 15.10 | 5.00 | 82.80 |
| bio18 | Precipitation warmest quarter (mm) | 991.21 | 547.52 | 286.40 | 3448.60 |
| bio19 | Precipitation coldest quarter (mm) | 37.67 | 18.86 | 7.40 | 94.60 |
| elevation | Elevation (m a.s.l.) | 2454.08 | 1271.20 | 113 | 5469 |
| slope | Terrain slope (°) | 27.70 | 11.63 | 0 | 71.39 |

> **Collinearity note:** Several bioclimatic predictors exhibit extreme multicollinearity (VIF > 10¹³ for bio5, bio6, bio7). CCA results are interpreted at the level of composite gradients, not individual predictors.

### 2.3 Forest Type Map

| Attribute | Value |
|-----------|-------|
| **Source** | Bhutan national forest-type map |
| **Assignment method** | Spatial join — nearest match to forest-type polygon boundaries |
| **Classes** | 12 (see Section 1.3) |

### 2.4 Soil Type

| Attribute | Value |
|-----------|-------|
| **Source** | Bhutan soil vector layer |
| **Assignment method** | Point-in-polygon spatial join; raster-based fallback where vector join failed |

---

## 3. MODIS Enhanced Vegetation Index (EVI)

| Attribute | Value |
|-----------|-------|
| **Product** | MODIS MOD13Q1 |
| **Temporal coverage** | 2000–2024 (25 annual observations) |
| **Spatial resolution** | 250 m |
| **Processing platform** | Google Earth Engine |
| **EVI scale** | [0, 1] reflectance scale |
| **Valid pixels (Bhutan)** | 703,900 pixels (39,032.2 km²) |

### 3.1 Derived Raster Products

| Product | Description |
|---------|-------------|
| **Theil–Sen slope raster** | Per-pixel monotonic trend magnitude (EVI yr⁻¹); Sen (1968) |
| **Mann–Kendall tau raster** | Per-pixel rank correlation coefficient |
| **Mann–Kendall p-value raster** | Per-pixel significance; where entirely missing, derived analytically from tau using the normal approximation with continuity correction (Mann, 1945; 25 observations assumed) |
| **Annual EVI composite stack** | Year-by-year EVI composites, 2000–2024 |

### 3.2 Trend Classification

Pixel-level EVI trends classified under two significance thresholds:

| Threshold | Greening (pixels / km²) | Browning (pixels / km²) | Stable (pixels / km²) |
|-----------|------------------------|------------------------|----------------------|
| Nominal (*p* ≤ 0.05) | 298,245 / 16,538.1 km² (42.37%) | 9,034 / 500.9 km² (1.28%) | 396,621 / 21,993.2 km² (56.35%) |
| BH-FDR corrected | 210,180 / 11,654.8 km² (29.86%) | 5,076 / 281.5 km² (0.72%) | 488,644 / 27,095.9 km² (69.42%) |

> Multiple-testing correction applied across 703,900 simultaneous pixel tests using the Benjamini–Hochberg false discovery rate (FDR) procedure (Benjamini & Hochberg, 1995).

### 3.3 Plot-level EVI Summaries

EVI Theil–Sen slope and Mann–Kendall trend class were extracted at each of the 1,942 NFI plot coordinates:

| Trend class | *n* plots |
|-------------|----------|
| Greening | 811 |
| Stable | 1,102 |
| Browning | 29 |

**EVI slope × biodiversity correlations:**
- EVI slope vs. species richness: Spearman ρ = 0.1256, *p* = 2.80 × 10⁻⁸
- EVI slope vs. SCI: Spearman ρ = 0.0968, *p* = 1.95 × 10⁻⁵

---

## 4. Derived Analytical Datasets

These datasets are generated by the pipeline and are not raw inputs:

| Dataset | Description | Pipeline module |
|---------|-------------|-----------------|
| `plot_points.gpkg` | GeoDataFrame of 1,942 plot centroids with all environmental variables | `02_env_extraction` |
| `veg_long.csv` | Long-format cleaned vegetation records (107,876 rows) | `01_data_cleaning` |
| `sp_mat.rds` | Species-by-plot matrix (plots × 2,185 species; pickle format) | `03_alpha_diversity` |
| `env_master.csv` | Environmental master table (1,942 plots × 24 variables) | `02_env_extraction` |

---

## 5. Data Availability

| Dataset | Availability |
|---------|-------------|
| Bhutan NFI vegetation records | Available upon reasonable request from the Department of Forests and Park Services, Royal Government of Bhutan |
| CMIP6 bioclimatic grids for Bhutan | Dorji et al. (2025) |
| MODIS MOD13Q1 EVI | Publicly available via NASA EARTHDATA / Google Earth Engine |
| DEM and terrain derivatives | Derived from publicly available DEM sources |
| Analysis code | This repository (`python/` pipeline) |

> The raw NFI data are not included in this repository as they are the property of the Royal Government of Bhutan. Access requests should be directed to the Department of Forests and Park Services (DFPS), Ministry of Energy and Natural Resources, Thimphu, Bhutan.

---

## 6. Reproducibility

All analyses were executed in Python 3.12. Stochastic procedures used a fixed random seed of **42** throughout (ordination initialisation, permutation tests, null-model simulations, network layout, bootstrap resampling). The pipeline is fully documented in `python/run_pipeline.py` and the 14 analysis modules under `python/modules/`.

```
Seed:           42
Permutations:   999 (PERMANOVA, ANOSIM, CCA, IndVal)
                99  (co-occurrence null model)
FDR method:     Benjamini–Hochberg
Python version: 3.12
```

---

*For questions about the data or pipeline, contact Wangdi (wangdiues@gmail.com).*
