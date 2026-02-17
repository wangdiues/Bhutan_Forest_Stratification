"""
Smoke tests for pipeline modules.

These tests verify that critical pipeline components work
end-to-end without errors. Tests are skipped if required
input data is not available.
"""

import pytest
from pathlib import Path


def test_module_registry_complete():
    """Verify all 14 modules are registered."""
    from python.run_pipeline import get_module_registry

    registry = get_module_registry()
    expected_ids = ["00", "01", "01b", "02", "02b", "03", "04",
                    "05", "06", "07", "08", "09", "10", "11"]
    actual_ids = [m["id"] for m in registry]

    assert len(actual_ids) == 14
    assert set(actual_ids) == set(expected_ids)


def test_module_registry_has_required_fields():
    """Verify registry entries have all required fields."""
    from python.run_pipeline import get_module_registry

    registry = get_module_registry()
    required_fields = ["id", "name", "file", "deps"]

    for module in registry:
        for field in required_fields:
            assert field in module, f"Module {module.get('id', 'unknown')} missing field '{field}'"


def test_module_registry_files_exist(project_root):
    """Verify all module files actually exist."""
    from python.run_pipeline import get_module_registry

    registry = get_module_registry()

    for module in registry:
        module_path = project_root / module["file"]
        assert module_path.exists(), f"Module file not found: {module_path}"


def test_dependency_parsing():
    """Test dependency string parsing."""
    from python.run_pipeline import parse_deps

    assert parse_deps("") == []
    assert parse_deps("01") == ["01"]
    assert parse_deps("01,02,03") == ["01", "02", "03"]
    assert parse_deps("01, 02, 03") == ["01", "02", "03"]


def test_module_id_normalization():
    """Test module ID normalization."""
    from python.run_pipeline import normalize_module_id

    assert normalize_module_id("0") == "00"
    assert normalize_module_id("1") == "01"
    assert normalize_module_id("01") == "01"
    assert normalize_module_id("1b") == "01b"
    assert normalize_module_id("01b") == "01b"


def test_dependency_expansion():
    """Test dependency resolution."""
    from python.run_pipeline import expand_dependencies, get_module_registry

    registry = get_module_registry()

    # Running module 03 should include 00, 01, 02, 03
    result = expand_dependencies(["03"], registry)
    assert "00" in result
    assert "01" in result
    assert "02" in result
    assert "03" in result
    assert result.index("00") < result.index("01")
    assert result.index("01") < result.index("02")
    assert result.index("02") < result.index("03")


@pytest.mark.skipif(
    not Path("raw_data").exists(),
    reason="Requires raw_data/ directory with input files"
)
def test_module_00_runs(config):
    """
    Smoke test: module 00 (data inspection) should run without errors.

    This is the simplest module - it just inventories data files.
    """
    from python.run_pipeline import run_module

    result = run_module("00", config)

    # Check result structure
    assert "status" in result
    assert "outputs" in result
    assert "warnings" in result
    assert "runtime_sec" in result

    # Module should succeed
    assert result["status"] == "success", f"Module 00 failed: {result.get('warnings', [])}"

    # Should produce output files
    assert len(result["outputs"]) > 0

    # Check outputs exist
    for path_str in result["outputs"]:
        output_path = Path(path_str)
        assert output_path.exists(), f"Output file not created: {output_path}"
        assert output_path.stat().st_size > 0, f"Output file is empty: {output_path}"


@pytest.mark.skipif(
    not Path("outputs/processed_data/veg_long.csv").exists(),
    reason="Requires module 01 outputs (veg_long.csv)"
)
def test_canonical_veg_long_has_content(config):
    """Verify veg_long.csv is non-empty and has expected columns."""
    import pandas as pd

    veg_long_path = config["paths"]["canonical"]["veg_long_csv"]
    veg_long = pd.read_csv(veg_long_path)

    assert len(veg_long) > 0, "veg_long.csv is empty"
    assert "plot_id" in veg_long.columns
    assert "species_name" in veg_long.columns

    # Optional columns that may exist
    for col in ["abundance", "forest_type", "stratum"]:
        if col in veg_long.columns:
            assert veg_long[col].notna().any(), f"Column '{col}' is all NaN"


@pytest.mark.skipif(
    not Path("outputs/processed_data/env_master.csv").exists(),
    reason="Requires module 02 outputs (env_master.csv)"
)
def test_canonical_env_master_has_content(config):
    """Verify env_master.csv is non-empty and has expected columns."""
    import pandas as pd

    env_path = config["paths"]["canonical"]["env_master_csv"]
    env_master = pd.read_csv(env_path)

    assert len(env_master) > 0, "env_master.csv is empty"
    assert "plot_id" in env_master.columns

    # Should have at least some environmental variables
    env_cols = [col for col in env_master.columns if col != "plot_id"]
    assert len(env_cols) > 0, "No environmental variables found"


@pytest.mark.skipif(
    not Path("outputs/processed_data/sp_mat.rds").exists(),
    reason="Requires module 01 outputs (sp_mat.rds)"
)
def test_canonical_species_matrix_loads(config):
    """Verify species matrix pickle file can be loaded."""
    from python.utils import load_pickle

    sp_mat_path = config["paths"]["canonical"]["sp_mat_rds"]
    sp_mat = load_pickle(sp_mat_path)

    assert sp_mat is not None
    assert hasattr(sp_mat, 'shape'), "Species matrix should be array-like"
    assert sp_mat.shape[0] > 0, "Species matrix has no rows"
    assert sp_mat.shape[1] > 0, "Species matrix has no columns"


def test_validation_module():
    """Test that validation module can be imported and used."""
    from python.validation import (
        ValidationError,
        validate_module_result,
        validate_csv,
        validate_pickle,
        validate_canonical_outputs
    )

    # Test ValidationError
    with pytest.raises(ValidationError):
        raise ValidationError("test error")

    # Test validate_module_result with invalid result
    invalid_result = {"status": "success"}  # Missing required keys
    with pytest.raises(ValidationError, match="missing required keys"):
        validate_module_result(invalid_result, "test")

    # Test validate_module_result with valid result
    valid_result = {
        "status": "success",
        "outputs": [],
        "warnings": [],
        "runtime_sec": 1.0
    }
    validate_module_result(valid_result, "test")  # Should not raise


def test_logging_setup(config):
    """Test that logging can be initialized."""
    from python.utils import setup_logging, get_module_logger

    logger = setup_logging(config, level="INFO")
    assert logger is not None
    assert logger.name == "bhutan_pipeline"

    # Test module logger
    module_logger = get_module_logger("test_module")
    assert module_logger.name == "bhutan_pipeline.test_module"


def test_config_detect_root(project_root):
    """Test that project root detection works."""
    from python.config import detect_project_root

    # Should detect root from current directory
    root = detect_project_root(project_root)
    assert root == project_root
    assert (root / "pyproject.toml").exists() or any(p.suffix == ".rproj" for p in root.iterdir() if p.is_file())


def test_input_snapshot_collection(config):
    """Test that input file snapshot works."""
    from python.run_pipeline import collect_input_snapshot

    snapshot = collect_input_snapshot(config)

    assert isinstance(snapshot, dict)
    assert len(snapshot) > 0

    # Each entry should have expected fields
    for key, info in snapshot.items():
        assert "path" in info
        assert "exists" in info
        assert "size_bytes" in info
        assert "mtime" in info
