"""
Pytest configuration and fixtures for the Bhutan pipeline test suite.
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def config():
    """Load actual project config."""
    from python.config import get_config
    return get_config()


@pytest.fixture
def sample_veg_data():
    """Minimal vegetation dataset for testing."""
    import pandas as pd
    return pd.DataFrame({
        'plot_id': ['P001', 'P001', 'P002', 'P002', 'P003'],
        'species_name': ['Quercus sp.', 'Pinus sp.', 'Quercus sp.', 'Betula sp.', 'Pinus sp.'],
        'abundance': [10, 5, 8, 3, 12],
        'latitude': [27.5, 27.5, 27.6, 27.7, 27.8],
        'longitude': [90.5, 90.5, 90.6, 90.7, 90.8],
        'forest_type': ['Broadleaf', 'Broadleaf', 'Mixed', 'Mixed', 'Conifer'],
        'stratum': ['Trees', 'Trees', 'Trees', 'Shrubs', 'Trees']
    })


@pytest.fixture
def sample_env_data():
    """Minimal environmental dataset for testing."""
    import pandas as pd
    return pd.DataFrame({
        'plot_id': ['P001', 'P002', 'P003'],
        'elevation': [2500, 2800, 3200],
        'bio1_temperature': [12.5, 10.2, 8.1],
        'bio12_ppt': [1200, 1500, 1800],
        'slope': [15, 25, 35],
        'aspect': [180, 90, 270]
    })


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory for test runs."""
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def project_root():
    """Return the project root path."""
    return Path(__file__).parent.parent
