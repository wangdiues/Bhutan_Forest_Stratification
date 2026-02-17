"""
Tests for configuration module.

Validates that the project configuration is correctly structured
and contains expected values.
"""

import pytest
from pathlib import Path


def test_config_has_required_keys(config):
    """Verify config structure has all required top-level keys."""
    assert "root" in config
    assert "paths" in config
    assert "params" in config
    assert "output" in config
    assert "columns" in config
    assert "colors" in config
    assert "packages" in config


def test_config_root_is_path(config):
    """Verify root is a valid Path object."""
    assert isinstance(config["root"], Path)
    assert config["root"].exists()


def test_config_paths_structure(config):
    """Verify paths section has required subsections."""
    paths = config["paths"]
    assert "inputs" in paths
    assert "canonical" in paths
    assert "logs" in paths
    assert isinstance(paths["inputs"], dict)
    assert isinstance(paths["canonical"], dict)


def test_config_params_types(config):
    """Verify parameter types are correct."""
    params = config["params"]
    assert isinstance(params["seed"], int)
    assert isinstance(params["permutations"], int)
    assert isinstance(params["dpi"], int)
    assert isinstance(params["cores"], int)
    assert isinstance(params["min_species_occurrence"], int)
    assert isinstance(params["min_group_size"], int)
    assert isinstance(params["min_time_points"], int)
    assert isinstance(params["outlier_iqr_multiplier"], (int, float))
    assert isinstance(params["correlation_flag_threshold"], (int, float))


def test_config_params_values(config):
    """Verify parameter values are sensible."""
    params = config["params"]
    assert params["seed"] >= 0
    assert params["permutations"] > 0
    assert params["dpi"] > 0
    assert params["cores"] >= 1
    assert params["min_species_occurrence"] >= 1
    assert params["min_group_size"] >= 1
    assert params["min_time_points"] >= 1
    assert params["outlier_iqr_multiplier"] > 0
    assert 0 < params["correlation_flag_threshold"] < 1


def test_bhutan_bbox_valid(config):
    """Verify Bhutan bounding box coordinates are sensible."""
    bbox = config["params"]["bhutan_bbox"]
    assert "lon_min" in bbox
    assert "lon_max" in bbox
    assert "lat_min" in bbox
    assert "lat_max" in bbox

    # Bhutan is roughly between these coordinates
    assert 88.7 <= bbox["lon_min"] <= 92.2
    assert 88.7 <= bbox["lon_max"] <= 92.2
    assert 26.7 <= bbox["lat_min"] <= 28.4
    assert 26.7 <= bbox["lat_max"] <= 28.4

    # Min should be less than max
    assert bbox["lon_min"] < bbox["lon_max"]
    assert bbox["lat_min"] < bbox["lat_max"]


def test_crs_epsg_valid(config):
    """Verify CRS EPSG code is valid."""
    assert config["params"]["crs_epsg"] == 4326  # WGS84


def test_canonical_columns_defined(config):
    """Verify canonical column names are defined."""
    columns = config["columns"]
    assert "canonical" in columns
    assert "mappings" in columns
    assert isinstance(columns["canonical"], list)
    assert isinstance(columns["mappings"], dict)
    assert len(columns["canonical"]) > 0


def test_column_mappings_valid(config):
    """Verify column mappings reference canonical columns."""
    mappings = config["columns"]["mappings"]
    canonical = config["columns"]["canonical"]

    # All mapping keys should be in canonical columns
    for key in mappings.keys():
        assert key in canonical, f"Mapping key '{key}' not in canonical columns"


def test_output_module_dirs_complete(config):
    """Verify all 14 modules have output directories defined."""
    module_dirs = config["output"]["module_dirs"]
    expected_modules = [
        "00_data_inspection",
        "01_data_cleaning",
        "01b_qc_after_cleaning",
        "02_env_extraction",
        "02b_qc_after_env_extraction",
        "03_alpha_diversity",
        "04_beta_diversity",
        "05_cca_ordination",
        "06_indicator_species",
        "07_co_occurrence",
        "08_evi_trends",
        "09_sci_index",
        "10_spatial_mapping",
        "11_reporting",
    ]

    for module in expected_modules:
        assert module in module_dirs, f"Module '{module}' missing from output dirs"


def test_color_palettes_defined(config):
    """Verify color palettes are defined for visualization."""
    colors = config["colors"]
    assert "strata" in colors
    assert "trend" in colors
    assert "continuous" in colors

    # Check strata colors
    assert "Trees" in colors["strata"]
    assert "Shrubs" in colors["strata"]
    assert "Herbs" in colors["strata"]

    # Verify hex color format
    for color_value in colors["strata"].values():
        assert color_value.startswith("#")
        assert len(color_value) == 7  # #RRGGBB format


def test_required_packages_listed(config):
    """Verify required Python packages are listed."""
    packages = config["packages"]
    essential = ["numpy", "pandas", "matplotlib", "scipy", "geopandas"]

    for pkg in essential:
        assert pkg in packages, f"Essential package '{pkg}' not in package list"
