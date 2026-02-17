## 2. Materials and Methods (Implementation-Aligned)

### 2.1 Study Area
The analysis covers Bhutan and uses geospatial predictors from DEM, climate rasters, forest type, and soil maps under `raw_data/`.

### 2.2 Data Sources
- Vegetation workbook: `raw_data/Vegetation Data.xlsx` (sheets: Trees, Shrubs, Herbs; Regeneration optional).
- Boundary: `raw_data/Bhutan/Bhutan.shp`.
- DEM: `raw_data/DEM_12/DEM_Bhutan_12.5NG.tif`.
- Climate rasters: `raw_data/Climate Rasters/Historical_1986-2015_bio1.tif` and `...bio12.tif` (plus additional BIO layers available).
- Forest type map: `raw_data/FTM_distribution/ForestTypeMap.shp`.
- Soil maps: vector `raw_data/Soil Type Map_Bhutan/Shapefile_Bhutan/Bhutan Soil map.shp` and raster fallback `.../Raster file_Bhutan/Reclass_soiltype.tif`.
- EVI time series: `raw_data/MODIS_EVI_2000_2024_Bhutan.csv`.

### 2.3 Pipeline and Reproducibility
The workflow is modular in Python (`python/modules/00` through `11`) and orchestrated by `python/run_pipeline.py`.
Run metadata are written to:
- `outputs/_run_logs/session_info.txt`
- `outputs/_run_logs/run_manifest.json`

### 2.4 Data Cleaning and Standardization
Vegetation sheets are merged into a long table and standardized to canonical names (`plot_id`, `species_name`, `stratum`, `longitude`, `latitude`, etc.) with flexible column mapping.
Key cleaning steps:
- trim/normalize text,
- enforce numeric coordinate parsing,
- remove empty plot/species records,
- write canonical outputs (`veg_long`, species matrix, plot points).

### 2.5 Spatial Alignment and Environmental Extraction
Plot coordinates are stored in EPSG:4326 and extracted against raster/vector covariates.
Implemented extraction includes:
- elevation from DEM,
- slope and aspect from DEM neighborhood gradients,
- BIO1-BIO19 raster extraction when available (with canonical outputs retained for BIO1 and BIO12),
- forest type attributes via spatial join,
- soil type via soil-vector join, with raster fallback.
Raster extraction is CRS-aware and transforms WGS84 plot coordinates into each raster CRS before sampling.

### 2.6 Diversity and Community Analyses
Implemented analyses include:
- alpha diversity (richness, Shannon, Simpson),
- NMDS ordination from Bray-Curtis dissimilarities,
- CCA via scikit-learn (site/species/environment scores),
- indicator species by forest groups with permutation p-values,
- species co-occurrence network analysis.

### 2.7 EVI Trend Processing
The pipeline computes Theil-Sen slope and Mann-Kendall p-values.
- If the EVI CSV contains plot identifiers and a valid time field, plot-level trends are produced.
- If `plot_id` is missing but coordinates are present, records are assigned to nearest plots for plot-level trends.
- If neither plot IDs nor usable coordinates are present, country-level trend is produced; if plot points are available from upstream modules, the country trend is replicated to plot points for map continuity.

### 2.8 Stratification Complexity Index (SCI)
SCI is computed by z-score aggregation of available diversity components:
- richness,
- Shannon,
- Simpson,
- stratum-specific richness components.

### 2.9 Reporting Outputs
The reporting module generates:
- `outputs/reports/pipeline_report.md`
- `outputs/reports/report_manifest.json`
- available summary CSVs when prerequisite module outputs exist.

### 2.10 Notes on Scope
This Python implementation provides a reproducible operational pipeline for the current dataset and output structure.
Methods that are commonly discussed in broader ecological study designs (e.g., GAM-specific model families, full beta turnover/nestedness decomposition, protected-area overlay with a PA shapefile) are not fully implemented unless corresponding modules and required inputs are added.
