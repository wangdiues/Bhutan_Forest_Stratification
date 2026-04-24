"""
Unit tests for validation module.

Tests the output validation layer for pipeline modules.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_creation(self):
        """Should create ValidationError with message."""
        from python.validation import ValidationError

        error = ValidationError("test message")
        assert str(error) == "test message"

    def test_validation_error_with_module(self):
        """Should create ValidationError with module context."""
        from python.validation import ValidationError

        error = ValidationError("test message", module="03")
        assert "test message" in str(error)


class TestValidateModuleResult:
    """Tests for validate_module_result function."""

    def test_valid_result_passes(self):
        """Should pass validation for valid result structure."""
        from python.validation import validate_module_result

        valid_result = {
            "status": "success",
            "outputs": ["/path/to/output.csv"],
            "warnings": [],
            "runtime_sec": 1.5,
        }

        # Should not raise
        validate_module_result(valid_result, "03")

    def test_missing_required_key_fails(self):
        """Should fail validation for missing required keys."""
        from python.validation import validate_module_result, ValidationError

        invalid_result = {"status": "success"}  # Missing outputs, warnings, runtime_sec

        with pytest.raises(ValidationError, match="missing required keys"):
            validate_module_result(invalid_result, "03")

    def test_invalid_status_fails(self):
        """Should fail validation for invalid status value."""
        from python.validation import validate_module_result, ValidationError

        invalid_result = {
            "status": "invalid_status",  # Must be "success" or "failed"
            "outputs": [],
            "warnings": [],
            "runtime_sec": 1.0,
        }

        with pytest.raises(ValidationError, match="Invalid status"):
            validate_module_result(invalid_result, "03")

    def test_outputs_must_be_list(self):
        """Should fail validation if outputs is not a list."""
        from python.validation import validate_module_result, ValidationError

        invalid_result = {
            "status": "success",
            "outputs": "/path/to/output.csv",  # Should be list
            "warnings": [],
            "runtime_sec": 1.0,
        }

        with pytest.raises(ValidationError, match="outputs must be a list"):
            validate_module_result(invalid_result, "03")

    def test_runtime_must_be_numeric(self):
        """Should fail validation if runtime is not numeric."""
        from python.validation import validate_module_result, ValidationError

        invalid_result = {
            "status": "success",
            "outputs": [],
            "warnings": [],
            "runtime_sec": "not a number",
        }

        with pytest.raises(ValidationError, match="runtime_sec must be numeric"):
            validate_module_result(invalid_result, "03")


class TestValidateCSV:
    """Tests for validate_csv function."""

    def test_valid_csv_passes(self, tmp_path):
        """Should pass validation for valid CSV file."""
        from python.validation import validate_csv

        csv_path = tmp_path / "test.csv"
        pd.DataFrame({"plot_id": [1, 2, 3], "value": [10, 20, 30]}).to_csv(
            csv_path, index=False
        )

        result = validate_csv(csv_path, required_columns=["plot_id"])

        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_file_fails(self, tmp_path):
        """Should fail validation for missing file."""
        from python.validation import validate_csv

        csv_path = tmp_path / "nonexistent.csv"

        result = validate_csv(csv_path, required_columns=["plot_id"])

        assert result.valid is False
        assert "does not exist" in result.errors[0]

    def test_missing_columns_fails(self, tmp_path):
        """Should fail validation for missing required columns."""
        from python.validation import validate_csv

        csv_path = tmp_path / "test.csv"
        pd.DataFrame({"plot_id": [1, 2, 3]}).to_csv(csv_path, index=False)

        result = validate_csv(csv_path, required_columns=["plot_id", "missing_column"])

        assert result.valid is False
        assert "missing_column" in result.errors[0]

    def test_empty_csv_warning(self, tmp_path):
        """Should add warning for empty CSV file."""
        from python.validation import validate_csv

        csv_path = tmp_path / "empty.csv"
        pd.DataFrame({"plot_id": []}).to_csv(csv_path, index=False)

        result = validate_csv(csv_path, required_columns=["plot_id"])

        assert result.valid is True  # Still valid, just empty
        assert len(result.warnings) > 0


class TestValidatePickle:
    """Tests for validate_pickle function."""

    def test_valid_pickle_passes(self, tmp_path):
        """Should pass validation for valid pickle file."""
        from python.validation import validate_pickle
        import pickle

        pkl_path = tmp_path / "test.pkl"
        test_data = {"key": "value"}
        with open(pkl_path, "wb") as f:
            pickle.dump(test_data, f)

        result = validate_pickle(pkl_path)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_pickle_fails(self, tmp_path):
        """Should fail validation for missing pickle file."""
        from python.validation import validate_pickle

        pkl_path = tmp_path / "nonexistent.pkl"

        result = validate_pickle(pkl_path)

        assert result.valid is False
        assert "does not exist" in result.errors[0]

    def test_empty_pickle_warning(self, tmp_path):
        """Should add warning for empty pickle file."""
        from python.validation import validate_pickle

        pkl_path = tmp_path / "empty.pkl"
        pkl_path.touch()  # Create empty file

        result = validate_pickle(pkl_path)

        assert result.valid is False  # Can't load empty file


class TestValidateGeoPackage:
    """Tests for validate_gpkg function."""

    def test_missing_gpkg_fails(self, tmp_path):
        """Should fail validation for missing GeoPackage."""
        from python.validation import validate_gpkg

        gpkg_path = tmp_path / "nonexistent.gpkg"

        result = validate_gpkg(gpkg_path)

        assert result.valid is False
        assert "does not exist" in result.errors[0]


class TestValidateCanonicalOutputs:
    """Tests for validate_canonical_outputs function."""

    def test_valid_canonical_outputs_pass(self, config, tmp_path):
        """Should pass validation when canonical outputs exist."""
        from python.validation import validate_canonical_outputs

        # Create required canonical files
        processed_dir = tmp_path / "outputs" / "processed_data"
        processed_dir.mkdir(parents=True)

        # Create veg_long.csv
        veg_path = processed_dir / "veg_long.csv"
        pd.DataFrame({
            "plot_id": [1, 2, 3],
            "species_name": ["sp1", "sp2", "sp3"],
            "stratum": ["Tree", "Shrub", "Herb"],
        }).to_csv(veg_path, index=False)

        # Update config to use tmp paths
        test_config = config.copy()
        test_config["paths"]["canonical"]["veg_long_csv"] = veg_path

        # Should not raise
        validate_canonical_outputs(test_config, "01")

    def test_missing_canonical_output_warning(self, config, tmp_path):
        """Should add warning for missing canonical output."""
        from python.validation import validate_canonical_outputs

        # Create empty processed dir
        processed_dir = tmp_path / "outputs" / "processed_data"
        processed_dir.mkdir(parents=True)

        # Update config to use tmp paths but don't create files
        test_config = config.copy()
        test_config["paths"]["canonical"]["veg_long_csv"] = (
            processed_dir / "veg_long.csv"
        )

        # Should not raise, but may log warning
        validate_canonical_outputs(test_config, "01")


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_creation(self):
        """Should create ValidationResult with defaults."""
        from python.validation import ValidationResult

        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_with_errors(self):
        """Should create ValidationResult with errors."""
        from python.validation import ValidationResult

        result = ValidationResult(valid=False, errors=["error1", "error2"])

        assert result.valid is False
        assert len(result.errors) == 2

    def test_str_representation(self):
        """Should have useful string representation."""
        from python.validation import ValidationResult

        result = ValidationResult(valid=False, errors=["test error"])

        str_repr = str(result)
        assert "valid" in str_repr.lower() or "error" in str_repr.lower()
