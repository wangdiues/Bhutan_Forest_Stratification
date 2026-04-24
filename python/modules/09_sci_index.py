from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as _stats

from python.utils import check_file, ensure_dirs, pub_style, safe_z, save_plot


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root = ensure_dirs("09_sci_index", config)
    out_plots = out_root / "plots"
    out_tables = out_root / "tables"

    alpha_path = config["output"]["module_dirs"]["03_alpha_diversity"] / "tables" / "alpha_diversity_summary.csv"
    check_file(alpha_path, "alpha diversity summary", required=True)

    alpha = pd.read_csv(alpha_path)

    # Use the alpha diversity table directly — module 03 already computes
    # richness_Herbs, richness_Shrubs, richness_Trees as columns in this table.
    # Reconstructing strata from veg_long and merging with add_prefix("richness_")
    # produces duplicate columns (richness_Herbs_x / richness_Herbs_y, r = 1.0)
    # that inflate those components' weight in the SCI z-score sum.
    sci = alpha.copy()
    if "shannon" not in sci.columns:
        raise RuntimeError("Alpha diversity table must include shannon column for SCI calculation.")

    base_cols = [c for c in ["richness", "shannon", "simpson"] if c in sci.columns]
    comp_cols = base_cols + [c for c in sci.columns if c.startswith("richness_")]
    for cc in comp_cols:
        sci[f"z_{cc}"] = safe_z(sci[cc])
    z_cols = [c for c in sci.columns if c.startswith("z_")]
    sci["sci_index"] = sci[z_cols].sum(axis=1, skipna=True)

    out_tbl      = out_tables / "stratification_complexity_index.csv"
    out_corr     = out_tables / "sci_component_correlations.csv"
    out_sens     = out_tables / "sci_sensitivity_analysis.csv"
    out_ft_summ  = out_tables / "sci_forest_type_summary.csv"
    sci.to_csv(out_tbl, index=False)

    # ── A9: Forest-type SCI summary with SE and 95% CI ───────────────────────
    # Small groups (n < 30) are flagged for interpretation caution.
    if "forest_type" in sci.columns and "sci_index" in sci.columns:
        ft_grp = sci.dropna(subset=["sci_index", "forest_type"]).groupby("forest_type")
        ft_rows = []
        for ft, grp_df in ft_grp:
            n     = len(grp_df)
            mean  = float(grp_df["sci_index"].mean())
            sd    = float(grp_df["sci_index"].std(ddof=1)) if n > 1 else float("nan")
            se    = sd / np.sqrt(n) if n > 0 and np.isfinite(sd) else float("nan")
            ci_lo = mean - 1.96 * se if np.isfinite(se) else float("nan")
            ci_hi = mean + 1.96 * se if np.isfinite(se) else float("nan")
            ft_rows.append({
                "forest_type":   str(ft),
                "n":             n,
                "sci_mean":      round(mean, 3),
                "sci_sd":        round(sd,   3) if np.isfinite(sd)    else float("nan"),
                "sci_se":        round(se,   3) if np.isfinite(se)    else float("nan"),
                "sci_ci95_lo":   round(ci_lo, 3) if np.isfinite(ci_lo) else float("nan"),
                "sci_ci95_hi":   round(ci_hi, 3) if np.isfinite(ci_hi) else float("nan"),
                "small_sample":  n < 30,
            })
        pd.DataFrame(ft_rows).sort_values("sci_mean", ascending=False).to_csv(
            out_ft_summ, index=False
        )

    # ── Component correlation matrix (Spearman) ───────────────────────────────
    z_data = sci[z_cols].dropna()
    if len(z_data) > 3 and len(z_cols) > 1:
        corr_rows = []
        for i, ca in enumerate(z_cols):
            for cb in z_cols[i + 1:]:
                r, p = _stats.spearmanr(z_data[ca], z_data[cb])
                corr_rows.append({
                    "component_a": ca,
                    "component_b": cb,
                    "spearman_r":  round(float(r), 4),
                    "p_value":     round(float(p), 6),
                })
        pd.DataFrame(corr_rows).to_csv(out_corr, index=False)

    # ── Leave-one-out sensitivity analysis ───────────────────────────────────
    # For each component, remove it, recompute SCI, measure Spearman r with full SCI.
    # High r → component is redundant / SCI is robust without it.
    # Low r → component is influential / its removal destabilises rankings.
    sens_rows = []
    full_sci = sci["sci_index"].dropna()
    for drop_col in z_cols:
        remaining = [c for c in z_cols if c != drop_col]
        if not remaining:
            continue
        sci_loo = sci[remaining].sum(axis=1, skipna=True)
        valid = full_sci.notna() & sci_loo.notna()
        r, p = _stats.spearmanr(full_sci[valid], sci_loo[valid])
        sens_rows.append({
            "component_dropped": drop_col,
            "spearman_r_with_full_sci": round(float(r), 4),
            "p_value": round(float(p), 6),
            "interpretation": (
                "robust (r ≥ 0.95)" if r >= 0.95
                else "moderate sensitivity (0.90 ≤ r < 0.95)" if r >= 0.90
                else "sensitive (r < 0.90)"
            ),
        })
    pd.DataFrame(sens_rows).to_csv(out_sens, index=False)

    if {"longitude", "latitude"}.issubset(sci.columns):
        with pub_style():
            fig, ax = plt.subplots(figsize=(8, 6))
            sc = ax.scatter(
                sci["longitude"], sci["latitude"],
                c=sci["sci_index"], cmap="RdYlGn",
                s=9, alpha=0.8, linewidths=0, rasterized=True,
            )
            cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
            cb.set_label("SCI (z-score sum)", fontsize=9)
            cb.ax.tick_params(labelsize=8)
            ax.set_title("Stratification Complexity Index (SCI)\nSpatial Distribution across Bhutan")
            ax.set_xlabel("Longitude (°E)")
            ax.set_ylabel("Latitude (°N)")
            ax.tick_params(labelsize=9)
            # Annotate range
            sci_valid = sci["sci_index"].dropna()
            ax.text(
                0.02, 0.98,
                f"Range: {sci_valid.min():.1f} – {sci_valid.max():.1f}\nMedian: {sci_valid.median():.1f}",
                transform=ax.transAxes, va="top", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.8", alpha=0.9),
            )
            fig.tight_layout()
            save_plot(fig, out_plots / "sci_spatial_map.png")

    return {
        "status": "success",
        "outputs": [str(out_tbl), str(out_corr), str(out_sens), str(out_ft_summ)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
