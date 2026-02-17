from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scipy import stats as _stats

from python.utils import (
    FOREST_PALETTE,
    check_columns,
    check_file,
    ensure_dirs,
    make_species_matrix,
    pub_style,
    save_pickle,
    save_plot,
)


def _shannon_row(values: np.ndarray) -> float:
    p = values[values > 0]
    if p.size == 0:
        return 0.0
    p = p / p.sum()
    return float(-(p * np.log(p)).sum())


def _simpson_row(values: np.ndarray) -> float:
    p = values[values > 0]
    if p.size == 0:
        return 0.0
    p = p / p.sum()
    return float(1 - (p**2).sum())


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root = ensure_dirs("03_alpha_diversity", config)
    out_plots = out_root / "plots"
    out_tables = out_root / "tables"
    out_data = out_root / "data"

    check_file(config["paths"]["canonical"]["veg_long_csv"], "veg_long", required=True)
    check_file(config["paths"]["canonical"]["env_master_csv"], "env_master", required=True)

    veg = pd.read_csv(config["paths"]["canonical"]["veg_long_csv"])
    env = pd.read_csv(config["paths"]["canonical"]["env_master_csv"])

    check_columns(veg, ["plot_id", "species_name", "stratum"])
    check_columns(env, ["plot_id"])

    sp_mat = make_species_matrix(veg)
    arr = sp_mat.to_numpy(dtype=float)

    richness = (arr > 0).sum(axis=1).astype(float)
    shannon = np.array([_shannon_row(row) for row in arr], dtype=float)
    simpson = np.array([_simpson_row(row) for row in arr], dtype=float)

    alpha = pd.DataFrame({
        "plot_id": sp_mat.index.astype(str),
        "richness": richness,
        "shannon": shannon,
        "simpson": simpson,
    })

    strata_rich = (
        veg[["plot_id", "stratum", "species_name"]]
        .drop_duplicates()
        .groupby(["plot_id", "stratum"]) 
        .size()
        .reset_index(name="stratum_richness")
        .pivot(index="plot_id", columns="stratum", values="stratum_richness")
        .fillna(0)
        .add_prefix("richness_")
        .reset_index()
    )

    alpha_full = alpha.merge(strata_rich, on="plot_id", how="left").merge(env, on="plot_id", how="left")

    f_data_csv = out_data / "alpha_diversity_complete.csv"
    f_data_rds = out_data / "alpha_diversity_complete.rds"
    f_table = out_tables / "alpha_diversity_summary.csv"

    alpha_full.to_csv(f_data_csv, index=False)
    save_pickle(f_data_rds, alpha_full)
    alpha_full.to_csv(f_table, index=False)

    if "elevation" in alpha_full.columns:
        x = pd.to_numeric(alpha_full["elevation"], errors="coerce")
        y = pd.to_numeric(alpha_full["richness"], errors="coerce")
        ok = x.notna() & y.notna()

        with pub_style():
            fig, ax = plt.subplots(figsize=(7, 5))

            # Scatter — colour by forest type when available
            if "forest_type" in alpha_full.columns:
                unique_fts = sorted(alpha_full.loc[ok, "forest_type"].astype(str).unique())
                cmap = {ft: FOREST_PALETTE[i % len(FOREST_PALETTE)] for i, ft in enumerate(unique_fts)}
                for ft in unique_fts:
                    mask = ok & (alpha_full["forest_type"].astype(str) == ft)
                    ax.scatter(x[mask], y[mask], color=cmap[ft], s=14, alpha=0.55,
                               linewidths=0, label=ft, rasterized=True)
                ax.legend(title="Forest type", bbox_to_anchor=(1.01, 1), loc="upper left",
                          framealpha=0.9, edgecolor="0.8", ncol=1, fontsize=8)
            else:
                ax.scatter(x[ok], y[ok], color=FOREST_PALETTE[0], s=14, alpha=0.55,
                           linewidths=0, rasterized=True)

            # Regression + 95 % confidence band
            if ok.sum() >= 4:
                slope, intercept, r_val, p_val, _ = _stats.linregress(x[ok], y[ok])
                xx = np.linspace(x[ok].min(), x[ok].max(), 300)
                yy = slope * xx + intercept
                ax.plot(xx, yy, color="#E15759", linewidth=1.8, linestyle="--",
                        zorder=5, label="Linear fit")
                n = int(ok.sum())
                resid_se = np.sqrt(((y[ok] - (slope * x[ok] + intercept)) ** 2).sum() / (n - 2))
                x_mean = x[ok].mean()
                margin = 1.96 * resid_se * np.sqrt(
                    1 / n + (xx - x_mean) ** 2 / ((x[ok] - x_mean) ** 2).sum()
                )
                ax.fill_between(xx, yy - margin, yy + margin,
                                color="#E15759", alpha=0.12, zorder=4)
                p_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.3f}"
                ax.text(
                    0.97, 0.97,
                    f"$R^2$ = {r_val ** 2:.3f},  {p_str}\nn = {n:,}",
                    transform=ax.transAxes, ha="right", va="top", fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.8", alpha=0.9),
                )

            ax.set_xlabel("Elevation (m a.s.l.)")
            ax.set_ylabel("Species richness")
            ax.set_title("Species Richness Along the Elevational Gradient")
            ax.set_xlim(left=0)
            ax.set_ylim(bottom=0)
            fig.tight_layout()
            save_plot(fig, out_plots / "richness_vs_elevation.png")

    return {
        "status": "success",
        "outputs": [str(f_data_csv), str(f_data_rds), str(f_table)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
