"""
Output validation layer for pipeline modules.

This module provides validation functions to ensure module outputs
meet contract requirements before being used by downstream modules.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import pandas as pd


class ValidationError(Exception):
    """Raised when module output validation fails."""
    pass


def validate_module_result(result: dict, module_id: str) -> None:
    """
    Validate module return contract and output files.

    Checks that:
    - All required keys are present (status, outputs, warnings, runtime_sec)
    - Status is valid ('success' or 'failed')
    - Success status doesn't contradict error presence
    - All claimed output files exist and are non-empty

    Args:
        result: Module result dictionary
        module_id: Module identifier for error messages

    Raises:
        ValidationError: If validation fails
    """
    required_keys = ["status", "outputs", "warnings", "runtime_sec"]
    missing = [k for k in required_keys if k not in result]
    if missing:
        raise ValidationError(
            f"Module {module_id} missing required keys: {missing}"
        )

    if result["status"] not in ["success", "failed"]:
        raise ValidationError(
            f"Module {module_id} invalid status: {result['status']}"
        )

    if result["status"] == "success" and "error" in result:
        raise ValidationError(
            f"Module {module_id} claims success but has error field"
        )

    # Validate output files exist and are non-empty
    for path_str in result["outputs"]:
        path = Path(path_str)
        if not path.exists():
            raise ValidationError(
                f"Module {module_id} claims output exists but not found: {path}"
            )
        if path.stat().st_size == 0:
            raise ValidationError(
                f"Module {module_id} created empty output: {path}"
            )


def validate_csv(path: Path, required_columns: list[str] | None = None, min_rows: int = 1) -> None:
    """
    Validate CSV file integrity.

    Args:
        path: Path to CSV file
        required_columns: Optional list of required column names
        min_rows: Minimum number of rows (default: 1)

    Raises:
        ValidationError: If validation fails
    """
    try:
        df = pd.read_csv(path, nrows=5)  # Quick check
        if len(df) == 0 and min_rows > 0:
            raise ValidationError(f"CSV is empty: {path}")
        if required_columns:
            missing = set(required_columns) - set(df.columns)
            if missing:
                raise ValidationError(
                    f"CSV missing columns {missing}: {path}"
                )
    except pd.errors.ParserError as e:
        raise ValidationError(f"CSV parse error in {path}: {e}") from e
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to validate CSV {path}: {e}") from e


def validate_pickle(path: Path) -> None:
    """
    Validate pickle file can be loaded.

    Args:
        path: Path to pickle file

    Raises:
        ValidationError: If validation fails
    """
    try:
        with open(path, 'rb') as f:
            obj = pickle.load(f)
        if obj is None:
            raise ValidationError(f"Pickle contains None: {path}")
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Pickle load error in {path}: {e}") from e


def validate_canonical_outputs(config: dict, module_id: str) -> None:
    """
    Validate critical canonical files exist after specific modules.

    Module dependencies:
    - 01: veg_long.csv, sp_mat.rds (pickle)
    - 02: env_master.csv
    - 03: All of the above should exist

    Args:
        config: Project configuration dictionary
        module_id: Module identifier (e.g., "01", "02", "03")

    Raises:
        ValidationError: If expected canonical files don't exist
    """
    checks = {
        "01": ["veg_long_csv", "sp_mat_rds"],
        "02": ["env_master_csv"],
        "03": ["veg_long_csv", "sp_mat_rds", "env_master_csv"]
    }

    if module_id not in checks:
        return

    for key in checks[module_id]:
        path = Path(config["paths"]["canonical"][key])
        if not path.exists():
            raise ValidationError(
                f"Module {module_id} should produce canonical file: {path}"
            )

        # Additional type-specific validation
        if path.suffix.lower() == '.csv':
            validate_csv(path)
        elif path.suffix.lower() in ['.rds', '.pkl', '.pickle']:
            validate_pickle(path)


def validate_gpkg(path: Path, geometry_type: str | None = None) -> None:
    """
    Validate GeoPackage file integrity.

    Args:
        path: Path to .gpkg file
        geometry_type: Optional expected geometry type (e.g., "Point", "Polygon")

    Raises:
        ValidationError: If validation fails
    """
    try:
        import geopandas as gpd

        gdf = gpd.read_file(path)
        if len(gdf) == 0:
            raise ValidationError(f"GeoPackage is empty: {path}")

        if geometry_type:
            actual_type = gdf.geometry.geom_type.iloc[0] if len(gdf) > 0 else None
            if actual_type != geometry_type:
                raise ValidationError(
                    f"GeoPackage has wrong geometry type. Expected: {geometry_type}, got: {actual_type}"
                )
    except ImportError:
        # geopandas not available, skip validation
        pass
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"GeoPackage validation error in {path}: {e}") from e
