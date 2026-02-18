from __future__ import annotations

import multiprocessing
from pathlib import Path
from typing import Any, Dict


def detect_project_root(start: str | Path | None = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    while True:
        has_rproj = any(p.suffix.lower() == ".rproj" for p in current.iterdir() if p.is_file())
        if has_rproj or (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            raise RuntimeError(
                "Could not locate project root. Ensure you run inside the repository containing pyproject.toml."
            )
        current = parent


def _case_insensitive_dir(root: Path, preferred: str) -> Path:
    exact = root / preferred
    if exact.exists():
        return exact
    lower_map = {p.name.lower(): p for p in root.iterdir() if p.is_dir()}
    return lower_map.get(preferred.lower(), exact)


def get_config() -> Dict[str, Any]:
    root = detect_project_root()

    raw_root = _case_insensitive_dir(root, "raw_data")
    data_root = raw_root if raw_root.exists() else _case_insensitive_dir(root, "data")
    output_root = root / "outputs"
    processed_root = output_root / "processed_data"

    config: Dict[str, Any] = {
        "root": root,
        "paths": {
            "inputs": {
                "vegetation_xlsx": data_root / "Vegetation Data.xlsx",
                "dem": data_root / "DEM_12" / "DEM_Bhutan_12.5NG.tif",
                "climate_bio1": data_root / "Climate Rasters" / "Historical_1986-2015_bio1.tif",
                "climate_bio12": data_root / "Climate Rasters" / "Historical_1986-2015_bio12.tif",
                "climate_dir": data_root / "Climate Rasters",
                "forest_type_map": data_root / "FTM_distribution" / "ForestTypeMap.shp",
                "bhutan_boundary": data_root / "Bhutan" / "Bhutan.shp",
                "evi_csv": data_root / "MODIS_EVI_2000_2024_Bhutan.csv",
                "evi_modis_dir": data_root / "Bhutan MODIS MOD13Q1 (V061) exports",
                "soil_map_vector": data_root / "Soil Type Map_Bhutan" / "Shapefile_Bhutan" / "Bhutan Soil map.shp",
                "soil_map_raster": data_root / "Soil Type Map_Bhutan" / "Raster file_Bhutan" / "Reclass_soiltype.tif",
            },
            "canonical": {
                "veg_long_csv": processed_root / "veg_long.csv",
                "veg_long_rds": processed_root / "veg_long.rds",
                "plot_points_gpkg": processed_root / "plot_points.gpkg",
                "sp_mat_rds": processed_root / "sp_mat.rds",
                "env_master_csv": processed_root / "env_master.csv",
                "env_master_rds": processed_root / "env_master.rds",
            },
            "compatibility": {
                "vegetation_data_cleaned_csv": processed_root / "vegetation_data_cleaned.csv",
                "plot_coordinates_cleaned_csv": processed_root / "plot_coordinates_cleaned.csv",
                "master_environmental_data_csv": processed_root / "master_environmental_data.csv",
                "master_environmental_data_with_ftm_csv": processed_root / "master_environmental_data_with_FTM.csv",
            },
            "logs": {
                "run_logs_dir": output_root / "_run_logs",
                "session_info": output_root / "_run_logs" / "session_info.txt",
                "run_manifest": output_root / "_run_logs" / "run_manifest.json",
            },
            "cache": {
                "cache_dir": output_root / "_cache",
                "module_cache": output_root / "_cache" / "module_cache.json",
                "profile_dir": output_root / "_cache" / "profiles",
            },
        },
        "output": {
            "root": output_root,
            "module_dirs": {
                "00_data_inspection": output_root / "data_inspection",
                "01_data_cleaning": processed_root,
                "01b_qc_after_cleaning": processed_root,
                "02_env_extraction": processed_root,
                "02b_qc_after_env_extraction": processed_root,
                "03_alpha_diversity": output_root / "alpha_diversity",
                "04_beta_diversity": output_root / "beta_diversity",
                "05_cca_ordination": output_root / "cca_ordination",
                "06_indicator_species": output_root / "indicator_species",
                "07_co_occurrence": output_root / "co_occurrence",
                "08_evi_trends": output_root / "evi_trends",
                "08b_evi_spatial": output_root / "evi_spatial",
                "09_sci_index": output_root / "sci_index",
                "10_spatial_mapping": output_root / "spatial_maps",
                "11_reporting": output_root / "reports",
            },
            "module_subdirs": {
                "03_alpha_diversity": ["plots", "tables", "data"],
                "04_beta_diversity": ["plots", "tables", "data"],
                "05_cca_ordination": ["plots", "tables", "models"],
                "06_indicator_species": ["plots", "tables"],
                "07_co_occurrence": ["plots", "tables", "models"],
                "08_evi_trends": ["plots", "tables"],
                "08b_evi_spatial": ["plots", "tables"],
                "09_sci_index": ["plots", "tables"],
            },
        },
        "params": {
            "crs_epsg": 4326,
            "bhutan_bbox": {"lon_min": 88.7, "lon_max": 92.2, "lat_min": 26.7, "lat_max": 28.4},
            "seed": 42,
            "permutations": 999,
            "dpi": 500,
            "cores": max(1, multiprocessing.cpu_count() - 1),
            "min_species_occurrence": 3,
            "min_group_size": 3,
            "min_time_points": 4,
            "outlier_iqr_multiplier": 1.5,
            "correlation_flag_threshold": 0.7,
            "extract_all_bioclim": True,
            "bio1_auto_scale": True,
            "bio1_scale_threshold_abs_c": 80.0,
        },
        "columns": {
            "canonical": [
                "plot_id",
                "forest_type",
                "stratum",
                "species_name",
                "abundance",
                "elevation",
                "longitude",
                "latitude",
                "slope",
                "aspect",
                "bio1_temperature",
                "bio12_ppt",
                "soil_type",
                "dzongkhag",
                "geog_name",
            ],
            "mappings": {
                "plot_id": ["plot_id", "plotid", "plot_no", "plot_number", "plotcode", "plot_code", "nfi_plot_number", "plot#", "plot"],
                "species_name": ["species_name", "scientific_name", "species", "sp_name"],
                "stratum": ["stratum", "layer", "vegetation_layer"],
                "longitude": ["longitude", "lon", "long", "x", "lon_dd"],
                "latitude": ["latitude", "lat", "y", "lat_dd"],
                "forest_type": ["forest_type", "fortyp", "for_typ", "foresttype"],
                "abundance": ["abundance", "count", "individuals", "n", "shrub_individuals_count", "herb_individuals_count"],
            },
        },
        "colors": {
            "strata": {"Trees": "#1B9E77", "Shrubs": "#D95F02", "Herbs": "#7570B3", "Regeneration": "#E7298A"},
            "trend": {"Greening": "#1B7837", "Browning": "#8C510A", "Stable": "#878787"},
            "continuous": ["#2166AC", "#67A9CF", "#D1E5F0", "#FDDBC7", "#EF8A62", "#B2182B"],
        },
        "packages": [
            "numpy",
            "pandas",
            "openpyxl",
            "matplotlib",
            "scipy",
            "scikit-learn",
            "networkx",
            "geopandas",
            "rasterio",
            "shapely",
        ],
    }

    return config


config = get_config()
