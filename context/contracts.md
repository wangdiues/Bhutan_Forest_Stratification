# Pipeline Contracts

## Global Rule
Each module file in `python/modules/` must expose:

```python
def module_run(config: dict) -> dict:
    return {
        "status": "success" | "failed",
        "outputs": list[str],
        "warnings": list[str],
        "runtime_sec": float,
    }
```

No module may rely on undeclared globals.

## Input Data Root
- Primary input root: `raw_data/`
- Fallback input root (legacy): `data/`
- Config source: `python/config.py`

## Canonical Data Contracts

### plot_points
- Path: `outputs/processed_data/plot_points.gpkg`
- Type: GeoPackage POINT layer
- Required columns: `plot_id`, `longitude`, `latitude`
- CRS: EPSG:4326

### veg_long
- Path: `outputs/processed_data/veg_long.csv`
- Type: long table
- Required columns: `plot_id`, `species_name`, `stratum`
- Optional columns: `abundance`, `longitude`, `latitude`

### sp_mat
- Path: `outputs/processed_data/sp_mat.rds`
- Type: serialized Python object (pickle; `.rds` extension kept for compatibility)
- Shape: plots x species
- Values: abundance where available, else presence/absence

### env_master
- Path: `outputs/processed_data/env_master.csv`
- Type: plot-level wide table
- Required columns: `plot_id`, `longitude`, `latitude`
- Typical predictors: `elevation`, `slope`, `aspect`, `bio1_temperature`, `bio12_ppt`, `soil_type`, `forest_type`

## Module I/O Contracts

### 00_data_inspection
- Inputs: all configured input/canonical/compatibility path targets
- Outputs: `outputs/data_inspection/data_inventory.csv`, `outputs/data_inspection/data_inventory.txt`

### 01_data_cleaning
- Inputs: `raw_data/Vegetation Data.xlsx`
- Outputs: canonical `veg_long`, `sp_mat`, `plot_points`; compatibility CSVs

### 01b_qc_after_cleaning
- Inputs: canonical `veg_long`, optional `plot_points`
- Outputs: QC CSVs and summary text under `outputs/processed_data/`

### 02_env_extraction
- Inputs: canonical `plot_points` + DEM/climate/soil/forest/EVI inputs from config
- Outputs: canonical `env_master` + compatibility environmental CSVs

### 02b_qc_after_env_extraction
- Inputs: canonical `env_master`
- Outputs: NA-rate, outlier, and collinearity QC tables

### 03_alpha_diversity
- Inputs: canonical `veg_long`, `env_master`
- Outputs: alpha diversity data/tables/plots under `outputs/alpha_diversity/`

### 04_beta_diversity
- Inputs: canonical `sp_mat`, `env_master`
- Outputs: NMDS scores, summary table, PERMANOVA text (when available)

### 05_cca_ordination
- Inputs: canonical `sp_mat`, `env_master`
- Outputs: CCA model object, site/species/environment score tables, CCA plot

### 06_indicator_species
- Inputs: canonical `sp_mat`, `env_master` with forest grouping (`forest_type` or `ForTyp`)
- Outputs: indicator tables and optional heatmap

### 07_co_occurrence
- Inputs: canonical `sp_mat`
- Outputs: graph model, node/edge metrics tables, network plot

### 08_evi_trends
- Inputs: EVI CSV, optional `plot_points`
- Outputs: trend table; spatial map only when plot-level trend IDs exist

### 09_sci_index
- Inputs: canonical `veg_long`, module 03 alpha summary
- Outputs: SCI table and optional SCI map

### 10_spatial_mapping
- Inputs: module outputs from 03/04/08/09 and optional Bhutan boundary
- Outputs: `spatial_master_points.gpkg` + map figures

### 11_reporting
- Inputs: available output tables/figures
- Outputs: `pipeline_report.md`, `report_manifest.json`, and available summary CSVs
