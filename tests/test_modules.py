"""
Unit tests for analytical logic in pipeline modules.

Tests the pure-function statistical calculations independently of
I/O, config, and file system, so they run without any raw data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers imported directly from modules
# ---------------------------------------------------------------------------

from python.utils import safe_z

# Module files have numeric prefixes, so they can't be imported via normal
# import machinery. Load them with importlib instead.
import importlib.util
from pathlib import Path

_BASE = Path(__file__).parent.parent / "python" / "modules"


def _load(filename: str):
    spec = importlib.util.spec_from_file_location(filename.replace(".py", ""), _BASE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod_alpha():
    return _load("03_alpha_diversity.py")


@pytest.fixture(scope="module")
def mod_indval():
    return _load("06_indicator_species.py")


@pytest.fixture(scope="module")
def mod_sci():
    return _load("09_sci_index.py")


# ---------------------------------------------------------------------------
# 03_alpha_diversity — Shannon & Simpson
# ---------------------------------------------------------------------------

class TestAlphaDiversityFunctions:
    def test_shannon_empty(self, mod_alpha):
        """All-zero row returns 0."""
        assert mod_alpha._shannon_row(np.zeros(5)) == 0.0

    def test_shannon_single_species(self, mod_alpha):
        """One species -> perfectly uniform -> H = 0."""
        assert mod_alpha._shannon_row(np.array([10.0])) == pytest.approx(0.0)

    def test_shannon_two_equal_species(self, mod_alpha):
        """Two equally abundant species -> H = ln(2) ≈ 0.693."""
        result = mod_alpha._shannon_row(np.array([1.0, 1.0]))
        assert result == pytest.approx(np.log(2), rel=1e-6)

    def test_shannon_five_equal_species(self, mod_alpha):
        """Five equally abundant species -> H = ln(5)."""
        arr = np.ones(5)
        result = mod_alpha._shannon_row(arr)
        assert result == pytest.approx(np.log(5), rel=1e-6)

    def test_shannon_ignores_zeros(self, mod_alpha):
        """Zeros in the array are excluded from calculation."""
        arr_full = np.array([1.0, 1.0, 1.0])
        arr_with_zeros = np.array([1.0, 1.0, 1.0, 0.0, 0.0])
        assert mod_alpha._shannon_row(arr_full) == pytest.approx(
            mod_alpha._shannon_row(arr_with_zeros), rel=1e-9
        )

    def test_shannon_scale_invariant(self, mod_alpha):
        """Doubling all abundances does not change Shannon index."""
        arr = np.array([2.0, 4.0, 6.0])
        assert mod_alpha._shannon_row(arr) == pytest.approx(
            mod_alpha._shannon_row(arr * 2), rel=1e-9
        )

    def test_simpson_empty(self, mod_alpha):
        """All-zero row returns 0."""
        assert mod_alpha._simpson_row(np.zeros(5)) == 0.0

    def test_simpson_single_species(self, mod_alpha):
        """One species -> D = 1 - 1^2 = 0."""
        assert mod_alpha._simpson_row(np.array([5.0])) == pytest.approx(0.0)

    def test_simpson_two_equal_species(self, mod_alpha):
        """Two equal species -> D = 1 - 0.5 = 0.5."""
        assert mod_alpha._simpson_row(np.array([1.0, 1.0])) == pytest.approx(0.5)

    def test_simpson_range(self, mod_alpha):
        """Simpson index is always in [0, 1)."""
        rng = np.random.default_rng(42)
        for _ in range(50):
            arr = rng.integers(0, 20, size=10).astype(float)
            val = mod_alpha._simpson_row(arr)
            assert 0.0 <= val < 1.0

    def test_simpson_scale_invariant(self, mod_alpha):
        """Scaling abundances does not change Simpson index."""
        arr = np.array([3.0, 1.0, 6.0])
        assert mod_alpha._simpson_row(arr) == pytest.approx(
            mod_alpha._simpson_row(arr * 100), rel=1e-9
        )


# ---------------------------------------------------------------------------
# 06_indicator_species — IndVal calculation
# ---------------------------------------------------------------------------

class TestIndVal:
    def _make_matrix(self):
        """Create a small known species matrix with two clear groups."""
        # 6 plots, 3 species: sp_A exclusive to group 0, sp_B to group 1
        sp = np.array([
            [5, 0, 2],  # plot 0 — group 0
            [4, 0, 1],  # plot 1 — group 0
            [6, 0, 3],  # plot 2 — group 0
            [0, 5, 1],  # plot 3 — group 1
            [0, 6, 2],  # plot 4 — group 1
            [0, 4, 1],  # plot 5 — group 1
        ], dtype=float)
        grp = np.array(["forest_A", "forest_A", "forest_A",
                         "forest_B", "forest_B", "forest_B"])
        return sp, grp, ["sp_A", "sp_B", "sp_C"]

    def test_calc_indval_returns_dataframe(self, mod_indval):
        sp, grp, names = self._make_matrix()
        result = mod_indval._calc_indval(sp, grp, names)
        assert isinstance(result, pd.DataFrame)
        assert set(result.columns) >= {"species_name", "group", "stat"}
        assert len(result) == 3  # one row per species

    def test_calc_indval_species_names_preserved(self, mod_indval):
        sp, grp, names = self._make_matrix()
        result = mod_indval._calc_indval(sp, grp, names)
        assert set(result["species_name"]) == set(names)

    def test_calc_indval_stat_range(self, mod_indval):
        """IndVal statistic should be in [0, 1] — strictly, with only float-epsilon tolerance."""
        sp, grp, names = self._make_matrix()
        result = mod_indval._calc_indval(sp, grp, names)
        assert (result["stat"] >= 0.0).all()
        # IndVal is mathematically bounded to [0, 1]; allow only sub-nanosecond float overshoot
        assert (result["stat"] <= 1.0 + 1e-12).all(), (
            f"IndVal exceeded 1.0: max={result['stat'].max():.16f}"
        )

    def test_calc_indval_exclusive_indicator(self, mod_indval):
        """sp_A occurs only in forest_A, so its best group should be forest_A."""
        sp, grp, names = self._make_matrix()
        result = mod_indval._calc_indval(sp, grp, names)
        row_a = result[result["species_name"] == "sp_A"].iloc[0]
        assert row_a["group"] == "forest_A"

    def test_calc_indval_exclusive_high_stat(self, mod_indval):
        """Perfectly exclusive species should have IndVal stat close to 1."""
        sp, grp, names = self._make_matrix()
        result = mod_indval._calc_indval(sp, grp, names)
        stat_a = result[result["species_name"] == "sp_A"]["stat"].iloc[0]
        stat_b = result[result["species_name"] == "sp_B"]["stat"].iloc[0]
        # Both perfectly exclusive species should have high stats
        assert stat_a > 0.7
        assert stat_b > 0.7

    def test_calc_indval_generalist_lower_stat(self, mod_indval):
        """sp_C present in both groups should have a lower IndVal than exclusive species."""
        sp, grp, names = self._make_matrix()
        result = mod_indval._calc_indval(sp, grp, names)
        stat_c = result[result["species_name"] == "sp_C"]["stat"].iloc[0]
        stat_a = result[result["species_name"] == "sp_A"]["stat"].iloc[0]
        assert stat_c < stat_a


# ---------------------------------------------------------------------------
# python.utils — safe_z (used by 09_sci_index)
# ---------------------------------------------------------------------------

class TestSafeZ:
    def test_safe_z_standard_case(self):
        """Normal z-score: mean-centered, unit variance."""
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        z = safe_z(s)
        assert z.mean() == pytest.approx(0.0, abs=1e-10)
        assert z.std(ddof=1) == pytest.approx(1.0, rel=1e-6)

    def test_safe_z_constant_returns_zero(self):
        """Constant series (zero std) returns all zeros, no division error."""
        s = pd.Series([7.0, 7.0, 7.0, 7.0])
        z = safe_z(s)
        assert (z == 0.0).all()

    def test_safe_z_single_value(self):
        """Single-element series returns zero."""
        s = pd.Series([42.0])
        z = safe_z(s)
        assert z.iloc[0] == 0.0

    def test_safe_z_preserves_length(self):
        """Output has same length as input."""
        s = pd.Series(range(20), dtype=float)
        assert len(safe_z(s)) == 20

    def test_safe_z_handles_nan(self):
        """NaNs in input propagate to output without crashing."""
        s = pd.Series([1.0, 2.0, float("nan"), 4.0])
        z = safe_z(s)
        assert len(z) == 4
        # At least some values should be non-NaN
        assert z.notna().any()


# ---------------------------------------------------------------------------
# 09_sci_index — SCI index is sum of z-scores
# ---------------------------------------------------------------------------

class TestSCIIndex:
    def test_sci_is_sum_of_z_scores(self):
        """SCI = sum of z-scored component columns — verify arithmetic."""
        from python.utils import safe_z

        df = pd.DataFrame({
            "plot_id": ["p1", "p2", "p3"],
            "richness": [10.0, 20.0, 30.0],
            "shannon":  [1.0,  2.0,  3.0],
        })
        df["z_richness"] = safe_z(df["richness"])
        df["z_shannon"] = safe_z(df["shannon"])
        df["sci_index"] = df[["z_richness", "z_shannon"]].sum(axis=1)

        # SCI values should sum to ~0 (z-scores are mean-centered)
        assert df["sci_index"].sum() == pytest.approx(0.0, abs=1e-10)

    def test_sci_ordering(self):
        """Plot with highest richness + diversity should have highest SCI."""
        from python.utils import safe_z

        df = pd.DataFrame({
            "plot_id": ["low", "mid", "high"],
            "richness": [5.0, 15.0, 25.0],
            "shannon":  [0.5, 1.5, 2.5],
        })
        df["z_richness"] = safe_z(df["richness"])
        df["z_shannon"] = safe_z(df["shannon"])
        df["sci_index"] = df[["z_richness", "z_shannon"]].sum(axis=1)

        assert df.loc[df["plot_id"] == "high", "sci_index"].iloc[0] > \
               df.loc[df["plot_id"] == "low", "sci_index"].iloc[0]
