"""
Unit tests for pipeline utility functions.

These tests verify individual functions work correctly
in isolation from the full pipeline.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import json


class TestEnsureDirs:
    """Tests for ensure_dirs utility function."""

    def test_ensure_dirs_creates_directory(self, tmp_path):
        """Should create directory if it doesn't exist."""
        from python.utils import ensure_dirs

        output_dir = tmp_path / "outputs" / "test_module"
        result = ensure_dirs("test_module", {"output": {"root": tmp_path / "outputs"}})

        assert result == output_dir
        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_ensure_dirs_uses_existing_directory(self, tmp_path):
        """Should use existing directory without error."""
        from python.utils import ensure_dirs

        output_dir = tmp_path / "outputs" / "test_module"
        output_dir.mkdir(parents=True)

        result = ensure_dirs("test_module", {"output": {"root": tmp_path / "outputs"}})

        assert result == output_dir


class TestSafeZ:
    """Tests for safe_z standardization function."""

    def test_safe_z_standardizes_array(self):
        """Should standardize array to zero mean and unit variance."""
        from python.utils import safe_z
        import numpy as np

        data = np.array([1, 2, 3, 4, 5], dtype=float)
        result = safe_z(data)

        assert np.isclose(result.mean(), 0, atol=1e-10)
        assert np.isclose(result.std(), 1, atol=1e-10)

    def test_safe_z_handles_constant_array(self):
        """Should handle constant array without division by zero."""
        from python.utils import safe_z
        import numpy as np

        data = np.array([5, 5, 5, 5, 5], dtype=float)
        result = safe_z(data)

        # All values should be 0 (or NaN) when std is 0
        assert all(np.isnan(result) | (result == 0))

    def test_safe_z_handles_empty_array(self):
        """Should handle empty array gracefully."""
        from python.utils import safe_z
        import numpy as np

        data = np.array([], dtype=float)
        result = safe_z(data)

        assert len(result) == 0


class TestLoadPickle:
    """Tests for pickle loading utility."""

    def test_load_pickle_loads_file(self, tmp_path):
        """Should load pickle file correctly."""
        from python.utils import load_pickle
        import pickle

        test_data = {"key": "value", "number": 42}
        pickle_path = tmp_path / "test.pkl"

        with open(pickle_path, "wb") as f:
            pickle.dump(test_data, f)

        result = load_pickle(pickle_path)

        assert result == test_data

    def test_load_pickle_returns_none_for_missing(self, tmp_path):
        """Should return None for missing file instead of raising."""
        from python.utils import load_pickle

        result = load_pickle(tmp_path / "nonexistent.pkl")

        assert result is None


class TestSavePickle:
    """Tests for pickle saving utility."""

    def test_save_pickle_saves_file(self, tmp_path):
        """Should save pickle file correctly."""
        from python.utils import save_pickle
        import pickle

        test_data = {"key": "value", "number": 42}
        pickle_path = tmp_path / "test.pkl"

        save_pickle(pickle_path, test_data)

        assert pickle_path.exists()

        with open(pickle_path, "rb") as f:
            result = pickle.load(f)

        assert result == test_data


class TestWriteJson:
    """Tests for JSON writing utility."""

    def test_write_json_writes_file(self, tmp_path):
        """Should write JSON file correctly."""
        from python.utils import write_json

        test_data = {"key": "value", "number": 42}
        json_path = tmp_path / "test.json"

        write_json(json_path, test_data)

        assert json_path.exists()

        with open(json_path) as f:
            result = json.load(f)

        assert result == test_data

    def test_write_json_pretty_print(self, tmp_path):
        """Should pretty print JSON when indent specified."""
        from python.utils import write_json

        test_data = {"key": "value", "nested": {"a": 1, "b": 2}}
        json_path = tmp_path / "test.json"

        write_json(json_path, test_data, indent=2)

        content = json_path.read_text()
        assert "\n" in content  # Pretty printed has newlines


class TestLogSection:
    """Tests for logging section decorator."""

    def test_log_section_prints_header(self, capsys):
        """Should print formatted section header."""
        from python.utils import log_section

        log_section("test section")

        captured = capsys.readouterr()
        assert "test section" in captured.out


class TestLogDone:
    """Tests for logging completion message."""

    def test_log_done_prints_completion(self, capsys):
        """Should print formatted completion message."""
        from python.utils import log_done

        log_done("test task")

        captured = capsys.readouterr()
        assert "test task" in captured.out


class TestNormalizeColumnName:
    """Tests for column name normalization."""

    def test_normalize_column_name_lowercase(self):
        """Should convert to lowercase."""
        from python.utils import normalize_column_name

        assert normalize_column_name("Plot_ID") == "plot_id"
        assert normalize_column_name("SPECIES_NAME") == "species_name"

    def test_normalize_column_name_strips_whitespace(self):
        """Should strip leading/trailing whitespace."""
        from python.utils import normalize_column_name

        assert normalize_column_name("  plot_id  ") == "plot_id"

    def test_normalize_column_name_replaces_spaces(self):
        """Should replace spaces with underscores."""
        from python.utils import normalize_column_name

        assert normalize_column_name("plot id") == "plot_id"
        assert normalize_column_name("forest type") == "forest_type"


class TestValidateElevation:
    """Tests for elevation validation."""

    def test_validate_elevation_within_range(self):
        """Should accept valid elevation values."""
        from python.utils import validate_elevation

        # Bhutan elevation range: 113-5469m (in dataset)
        assert validate_elevation(1000, -10, 6000) is True
        assert validate_elevation(3000, -10, 6000) is True

    def test_validate_elevation_out_of_range(self):
        """Should reject out-of-range elevation values."""
        from python.utils import validate_elevation

        assert validate_elevation(-100, -10, 6000) is False
        assert validate_elevation(10000, -10, 6000) is False


class TestValidateCoordinates:
    """Tests for coordinate validation."""

    def test_validate_coordinates_valid_bbox(self):
        """Should accept coordinates within Bhutan bbox."""
        from python.utils import validate_coordinates

        # Bhutan bbox: lon 88.7-92.2, lat 26.7-28.4
        assert validate_coordinates(90.0, 27.5, 88.7, 92.2, 26.7, 28.4) is True

    def test_validate_coordinates_outside_bbox(self):
        """Should reject coordinates outside Bhutan bbox."""
        from python.utils import validate_coordinates

        assert validate_coordinates(85.0, 27.5, 88.7, 92.2, 26.7, 28.4) is False
        assert validate_coordinates(90.0, 30.0, 88.7, 92.2, 26.7, 28.4) is False


class TestFormatRuntime:
    """Tests for runtime formatting utility."""

    def test_format_runtime_seconds(self):
        """Should format runtime in seconds."""
        from python.utils import format_runtime

        assert format_runtime(5.5) == "5.5s"

    def test_format_runtime_minutes(self):
        """Should format runtime in minutes when > 60s."""
        from python.utils import format_runtime

        assert "min" in format_runtime(125.0)

    def test_format_runtime_hours(self):
        """Should format runtime in hours when > 3600s."""
        from python.utils import format_runtime

        assert "hr" in format_runtime(7200.0)


class TestMemoryFormat:
    """Tests for memory formatting utility."""

    def test_format_memory_bytes(self):
        """Should format small memory in bytes."""
        from python.utils import format_memory

        assert "B" in format_memory(512)

    def test_format_memory_mb(self):
        """Should format medium memory in MB."""
        from python.utils import format_memory

        result = format_memory(100 * 1024 * 1024)  # 100 MB
        assert "MB" in result

    def test_format_memory_gb(self):
        """Should format large memory in GB."""
        from python.utils import format_memory

        result = format_memory(2 * 1024 * 1024 * 1024)  # 2 GB
        assert "GB" in result
