from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for thread-safe parallel execution
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from utils import check_columns, check_file, ensure_dirs, make_species_matrix, save_pickle, save_plot
except ImportError:
    from python.utils import check_columns, check_file, ensure_dirs, make_species_matrix, save_pickle, save_plot


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
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(alpha_full["elevation"], alpha_full["richness"], alpha=0.6)
        x = pd.to_numeric(alpha_full["elevation"], errors="coerce")
        y = pd.to_numeric(alpha_full["richness"], errors="coerce")
        ok = x.notna() & y.notna()
        if ok.sum() >= 2:
            b1, b0 = np.polyfit(x[ok], y[ok], 1)
            xx = np.linspace(x[ok].min(), x[ok].max(), 200)
            ax.plot(xx, b1 * xx + b0, linewidth=1)
        ax.set_title("Species Richness vs Elevation")
        ax.set_xlabel("Elevation")
        ax.set_ylabel("Richness")
        save_plot(fig, out_plots / "richness_vs_elevation.png")

    return {
        "status": "success",
        "outputs": [str(f_data_csv), str(f_data_rds), str(f_table)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
