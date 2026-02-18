"""Result caching system for incremental pipeline execution.

This module provides hash-based change detection to skip modules
whose inputs and parameters haven't changed since the last run.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

try:
    from config import config
    from utils import write_json
except ImportError:
    from python.config import config
    from python.utils import write_json


def hash_file(file_path: str | Path) -> str:
    """
    Compute SHA-256 hash of a file's contents.

    Args:
        file_path: Path to file

    Returns:
        Hex digest of file hash, or "missing" if file doesn't exist
    """
    path = Path(file_path)
    if not path.exists():
        return "missing"

    hasher = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        return f"error:{type(e).__name__}"


def hash_string(text: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_config_params(params: Dict[str, Any]) -> str:
    """
    Hash relevant configuration parameters.

    Args:
        params: Configuration parameters dictionary

    Returns:
        Hash of serialized parameters
    """
    # Extract cacheable parameters (exclude dynamic ones like cores)
    cacheable_keys = [
        "seed",
        "permutations",
        "dpi",
        "min_species_occurrence",
        "min_group_size",
        "min_time_points",
        "outlier_iqr_multiplier",
        "correlation_flag_threshold",
        "extract_all_bioclim",
        "bio1_auto_scale",
        "bio1_scale_threshold_abs_c",
        "crs_epsg",
    ]

    cacheable = {k: params.get(k) for k in cacheable_keys if k in params}
    # Sort keys for deterministic hashing
    serialized = json.dumps(cacheable, sort_keys=True)
    return hash_string(serialized)


def get_module_inputs(module_id: str, cfg: dict) -> List[Path]:
    """
    Determine input files for a given module.

    Args:
        module_id: Module identifier (e.g., "01", "03")
        cfg: Configuration dictionary

    Returns:
        List of input file paths
    """
    canonical = cfg["paths"]["canonical"]
    inputs_cfg = cfg["paths"]["inputs"]

    # Map module IDs to their input dependencies
    input_map = {
        "00": [
            inputs_cfg.get("vegetation_xlsx"),
            inputs_cfg.get("dem"),
            inputs_cfg.get("climate_bio1"),
            inputs_cfg.get("climate_bio12"),
        ],
        "01": [inputs_cfg.get("vegetation_xlsx")],
        "01b": [canonical.get("veg_long_csv"), canonical.get("plot_points_gpkg")],
        "02": [
            canonical.get("plot_points_gpkg"),
            inputs_cfg.get("dem"),
            inputs_cfg.get("climate_dir"),
            inputs_cfg.get("forest_type_map"),
            inputs_cfg.get("soil_map_raster"),
        ],
        "02b": [canonical.get("env_master_csv")],
        "03": [canonical.get("veg_long_csv"), canonical.get("sp_mat_rds"), canonical.get("env_master_csv")],
        "04": [canonical.get("veg_long_csv"), canonical.get("sp_mat_rds"), canonical.get("env_master_csv")],
        "05": [canonical.get("veg_long_csv"), canonical.get("sp_mat_rds"), canonical.get("env_master_csv")],
        "06": [canonical.get("veg_long_csv"), canonical.get("sp_mat_rds"), canonical.get("env_master_csv")],
        "07": [canonical.get("veg_long_csv"), canonical.get("sp_mat_rds"), canonical.get("env_master_csv")],
        "08": [inputs_cfg.get("evi_csv"), canonical.get("env_master_csv")],
        "09": [canonical.get("veg_long_csv"), canonical.get("sp_mat_rds"), canonical.get("env_master_csv")],
        "10": [canonical.get("env_master_csv")],
        "11": [canonical.get("env_master_csv")],
    }

    # Get inputs for this module, filter out None values
    module_inputs = input_map.get(module_id, [])
    return [Path(p) for p in module_inputs if p is not None]


def get_module_outputs(module_id: str, cfg: dict) -> List[Path]:
    """
    Determine expected output files for a module.

    Args:
        module_id: Module identifier
        cfg: Configuration dictionary

    Returns:
        List of output file paths
    """
    output_dirs = cfg["output"]["module_dirs"]

    # Map modules to their key outputs
    # We'll check these exist to validate the cache
    output_map = {
        "00": [output_dirs["00_data_inspection"] / "data_inventory.csv"],
        "01": [
            cfg["paths"]["canonical"]["veg_long_csv"],
            cfg["paths"]["canonical"]["plot_points_gpkg"],
        ],
        "01b": [],  # QC module, no primary outputs
        "02": [cfg["paths"]["canonical"]["env_master_csv"]],
        "02b": [],  # QC module
        "03": [output_dirs["03_alpha_diversity"] / "data" / "alpha_diversity_results.pkl"],
        "04": [output_dirs["04_beta_diversity"] / "data" / "beta_diversity_results.pkl"],
        "05": [output_dirs["05_cca_ordination"] / "models" / "cca_model.pkl"],
        "06": [output_dirs["06_indicator_species"] / "tables" / "indicator_species.csv"],
        "07": [output_dirs["07_co_occurrence"] / "tables" / "co_occurrence_matrix.csv"],
        "08": [output_dirs["08_evi_spatial"] / "tables" / "plot_evi_trends.csv"],
        "09": [output_dirs["09_sci_index"] / "tables" / "sci_scores.csv"],
        "10": [output_dirs["10_spatial_mapping"] / "composite_map.png"],
        "11": [output_dirs["11_reporting"] / "pipeline_summary_report.html"],
    }

    outputs = output_map.get(module_id, [])
    return [Path(p) for p in outputs if p is not None]


def compute_module_hash(module_id: str, cfg: dict) -> str:
    """
    Compute composite hash for a module based on inputs and parameters.

    Args:
        module_id: Module identifier
        cfg: Configuration dictionary

    Returns:
        Combined hash string
    """
    hash_components = []

    # Hash input files
    input_files = get_module_inputs(module_id, cfg)
    for input_file in input_files:
        file_hash = hash_file(input_file)
        hash_components.append(f"{input_file.name}:{file_hash}")

    # Hash configuration parameters
    param_hash = hash_config_params(cfg["params"])
    hash_components.append(f"params:{param_hash}")

    # Combine all hashes
    combined = "|".join(sorted(hash_components))
    return hash_string(combined)


def load_cache(cfg: dict) -> dict:
    """
    Load module cache from disk.

    Args:
        cfg: Configuration dictionary

    Returns:
        Cache dictionary mapping module_id -> {hash, timestamp, outputs}
    """
    cache_file = Path(cfg["paths"]["cache"]["module_cache"])

    if not cache_file.exists():
        return {}

    try:
        with open(cache_file, "r") as f:
            return json.load(f)
    except Exception:
        # If cache is corrupted, start fresh
        return {}


def save_cache(cache: dict, cfg: dict) -> None:
    """
    Save module cache to disk.

    Args:
        cache: Cache dictionary
        cfg: Configuration dictionary
    """
    cache_file = Path(cfg["paths"]["cache"]["module_cache"])
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    write_json(cache_file, cache)


def should_skip_module(
    module_id: str, cfg: dict, cache: dict | None = None, logger: logging.Logger | None = None
) -> tuple[bool, str]:
    """
    Determine if a module can be skipped based on cache.

    Args:
        module_id: Module identifier
        cfg: Configuration dictionary
        cache: Existing cache dictionary (will load if None)
        logger: Optional logger for debug output

    Returns:
        Tuple of (should_skip: bool, reason: str)
    """
    if cache is None:
        cache = load_cache(cfg)

    # Compute current hash
    current_hash = compute_module_hash(module_id, cfg)

    # Check if module is in cache
    if module_id not in cache:
        reason = "no cache entry"
        if logger:
            logger.debug(f"Module {module_id}: {reason}")
        return False, reason

    cached_entry = cache[module_id]
    cached_hash = cached_entry.get("hash")

    # Check if hash matches
    if cached_hash != current_hash:
        reason = "inputs or parameters changed"
        if logger:
            logger.debug(f"Module {module_id}: {reason}")
        return False, reason

    # Verify outputs still exist
    expected_outputs = get_module_outputs(module_id, cfg)
    missing_outputs = [str(p) for p in expected_outputs if not p.exists()]

    if missing_outputs:
        reason = f"outputs missing: {missing_outputs[:2]}"  # Show first 2
        if logger:
            logger.debug(f"Module {module_id}: {reason}")
        return False, reason

    # All checks passed - safe to skip
    reason = "cache hit"
    if logger:
        logger.info(f"Module {module_id}: skipping (cache hit)")
    return True, reason


def update_cache_entry(module_id: str, cfg: dict, cache: dict) -> None:
    """
    Update cache entry after successful module execution.

    Args:
        module_id: Module identifier
        cfg: Configuration dictionary
        cache: Cache dictionary to update (modified in-place)
    """
    import time

    module_hash = compute_module_hash(module_id, cfg)
    outputs = [str(p) for p in get_module_outputs(module_id, cfg) if p.exists()]

    cache[module_id] = {
        "hash": module_hash,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "outputs": outputs,
    }


def clear_cache(cfg: dict, logger: logging.Logger | None = None) -> None:
    """
    Clear the module cache.

    Args:
        cfg: Configuration dictionary
        logger: Optional logger
    """
    cache_file = Path(cfg["paths"]["cache"]["module_cache"])

    if cache_file.exists():
        cache_file.unlink()
        if logger:
            logger.info(f"Cache cleared: {cache_file}")
    else:
        if logger:
            logger.debug("No cache file to clear")
