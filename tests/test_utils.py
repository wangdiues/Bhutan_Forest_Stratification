"""
Tests for utility functions.

Validates that shared utility functions work correctly
across various input scenarios.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path


def test_normalize_name():
    """Test name normalization function."""
    from python.utils import normalize_name

    assert normalize_name("Plot_ID") == "plotid"
    assert normalize_name("Species Name") == "speciesname"
    assert normalize_name("Bio1-Temperature") == "bio1temperature"
    assert normalize_name("  PLOT  ID  ") == "plotid"
    assert normalize_name("123abc") == "123abc"


def test_clean_sp_names(sample_veg_data):
    """Test species name cleaning."""
    from python.utils import clean_sp_names

    # Create test series with messy names
    series = pd.Series(["  Quercus sp. ", "Pinus  edulis", "Betula ", "  Oak  Tree  "])
    cleaned = clean_sp_names(series)

    assert cleaned[0] == "Quercus sp."
    assert cleaned[1] == "Pinus edulis"
    assert cleaned[2] == "Betula"
    assert cleaned[3] == "Oak Tree"

    # Test that it preserves scientific naming conventions
    assert "  " not in cleaned.values[0]  # No double spaces


def test_make_species_matrix(sample_veg_data):
    """Test species matrix creation."""
    from python.utils import make_species_matrix

    mat = make_species_matrix(sample_veg_data)

    # Should have 3 plots (rows) and 3 species (columns)
    assert mat.shape == (3, 3)  # P001, P002, P003 x Quercus, Pinus, Betula

    # Check species are in columns
    assert "Quercus sp." in mat.columns
    assert "Pinus sp." in mat.columns
    assert "Betula sp." in mat.columns

    # Check plot IDs are in index
    assert "P001" in mat.index
    assert "P002" in mat.index
    assert "P003" in mat.index

    # Verify abundance values
    assert mat.loc["P001", "Quercus sp."] == 10
    assert mat.loc["P001", "Pinus sp."] == 5
    assert mat.loc["P002", "Quercus sp."] == 8


def test_make_species_matrix_no_abundance():
    """Test species matrix creation without abundance column."""
    from python.utils import make_species_matrix

    df = pd.DataFrame({
        'plot_id': ['P1', 'P1', 'P2'],
        'species_name': ['Oak', 'Pine', 'Oak']
    })

    mat = make_species_matrix(df)

    # Should use presence (1.0) when no abundance
    assert mat.loc["P1", "Oak"] == 1.0
    assert mat.loc["P1", "Pine"] == 1.0
    assert mat.loc["P2", "Oak"] == 1.0


def test_safe_z():
    """Test safe z-score calculation."""
    from python.utils import safe_z

    # Normal case - should standardize to mean=0, std=1
    s = pd.Series([1, 2, 3, 4, 5])
    z = safe_z(s)
    assert abs(z.mean()) < 1e-10
    assert abs(z.std() - 1.0) < 1e-10

    # Zero variance - should return zeros
    s_const = pd.Series([5, 5, 5, 5])
    z_const = safe_z(s_const)
    assert (z_const == 0).all()

    # With NaN values
    s_nan = pd.Series([1, 2, np.nan, 4, 5])
    z_nan = safe_z(s_nan)
    assert not z_nan.isna().all()  # Should handle NaN


def test_standardize_columns():
    """Test column name standardization."""
    from python.utils import standardize_columns

    df = pd.DataFrame({
        'Plot_ID': [1, 2, 3],
        'ForTyp': ['A', 'B', 'C'],
        'SpeciesName': ['Oak', 'Pine', 'Birch']
    })

    mapping = {
        'plot_id': ['plot_id', 'plotid', 'plot_no'],
        'forest_type': ['forest_type', 'fortyp', 'for_typ'],
        'species_name': ['species_name', 'speciesname']
    }

    result = standardize_columns(df, mapping)

    # Should have canonical names
    assert 'plot_id' in result.columns
    assert 'forest_type' in result.columns
    assert 'species_name' in result.columns

    # Forest type should be string
    assert result['forest_type'].dtype == object


def test_check_columns():
    """Test column presence validation."""
    from python.utils import check_columns

    df = pd.DataFrame({
        'col_a': [1, 2, 3],
        'col_b': [4, 5, 6]
    })

    # Should pass when columns exist
    check_columns(df, ['col_a', 'col_b'])

    # Should raise when columns missing
    with pytest.raises(RuntimeError, match="Missing required columns"):
        check_columns(df, ['col_a', 'col_c'])


def test_check_file(tmp_path):
    """Test file existence checking."""
    from python.utils import check_file

    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    # Should return True for existing file
    assert check_file(test_file, "Test file", required=False) is True

    # Should raise for missing required file
    missing_file = tmp_path / "missing.txt"
    with pytest.raises(RuntimeError, match="not found"):
        check_file(missing_file, "Missing file", required=True)

    # Should return False for missing non-required file
    assert check_file(missing_file, "Missing file", required=False) is False


def test_save_and_load_pickle(tmp_path):
    """Test pickle save and load functions."""
    from python.utils import save_pickle, load_pickle

    test_data = {
        'key1': 'value1',
        'key2': [1, 2, 3],
        'key3': pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    }

    pickle_path = tmp_path / "test.pkl"
    save_pickle(pickle_path, test_data)

    assert pickle_path.exists()

    loaded_data = load_pickle(pickle_path)
    assert loaded_data['key1'] == test_data['key1']
    assert loaded_data['key2'] == test_data['key2']
    assert loaded_data['key3'].equals(test_data['key3'])


def test_as_plain_matrix():
    """Test conversion to plain numpy matrix."""
    from python.utils import as_plain_matrix

    # From DataFrame
    df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    mat = as_plain_matrix(df)
    assert isinstance(mat, np.ndarray)
    assert mat.dtype == np.float64
    assert mat.shape == (2, 2)

    # From array
    arr = np.array([[1, 2], [3, 4]])
    mat = as_plain_matrix(arr)
    assert isinstance(mat, np.ndarray)
    assert mat.dtype == np.float64


def test_ensure_dirs(config, tmp_path):
    """Test directory creation utility."""
    from python.utils import ensure_dirs

    # This should work with actual config
    result = ensure_dirs("00_data_inspection", config)
    assert isinstance(result, Path)


def test_load_packages():
    """Test package availability checker."""
    from python.utils import load_packages

    # Should pass for installed packages
    load_packages(["numpy", "pandas"])

    # Should raise for missing packages
    with pytest.raises(RuntimeError, match="Missing Python packages"):
        load_packages(["nonexistent_package_xyz123"])
