from __future__ import annotations

import time

import matplotlib.pyplot as plt
import pandas as pd

from python.utils import check_file, ensure_dirs, pub_style, safe_z, save_plot


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root = ensure_dirs("09_sci_index", config)
    out_plots = out_root / "plots"
    out_tables = out_root / "tables"

    alpha_path = config["output"]["module_dirs"]["03_alpha_diversity"] / "tables" / "alpha_diversity_summary.csv"
    check_file(config["paths"]["canonical"]["veg_long_csv"], "veg_long", required=True)
    check_file(alpha_path, "alpha diversity summary", required=True)

    veg = pd.read_csv(config["paths"]["canonical"]["veg_long_csv"])
    alpha = pd.read_csv(alpha_path)

    strata = (
        veg[["plot_id", "stratum", "species_name"]]
        .drop_duplicates()
        .groupby(["plot_id", "stratum"])
        .size()
        .reset_index(name="n_species")
        .pivot(index="plot_id", columns="stratum", values="n_species")
        .fillna(0)
        .add_prefix("richness_")
        .reset_index()
    )

    sci = alpha.merge(strata, on="plot_id", how="left")
    if "shannon" not in sci.columns:
        raise RuntimeError("Alpha diversity table must include shannon column for SCI calculation.")

    base_cols = [c for c in ["richness", "shannon", "simpson"] if c in sci.columns]
    comp_cols = base_cols + [c for c in sci.columns if c.startswith("richness_")]
    for cc in comp_cols:
        sci[f"z_{cc}"] = safe_z(sci[cc])
    z_cols = [c for c in sci.columns if c.startswith("z_")]
    sci["sci_index"] = sci[z_cols].sum(axis=1, skipna=True)

    out_tbl = out_tables / "stratification_complexity_index.csv"
    sci.to_csv(out_tbl, index=False)

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
        "outputs": [str(out_tbl)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
