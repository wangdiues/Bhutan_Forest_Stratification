from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from python.utils import check_file, ensure_dirs, load_pickle, pub_style, save_plot


def _calc_indval(sp: np.ndarray, grp: np.ndarray, species_names: list[str]) -> pd.DataFrame:
    groups = np.unique(grp)
    rows = []
    occ = (sp > 0).astype(float)
    for j, sname in enumerate(species_names):
        x = occ[:, j]
        group_means = {g: x[grp == g].mean() if np.any(grp == g) else 0 for g in groups}
        best_group = max(group_means, key=group_means.get)
        A = group_means[best_group] / (sum(group_means.values()) + 1e-12)
        B = x[grp == best_group].mean() if np.any(grp == best_group) else 0
        stat = A * B
        rows.append({"species_name": sname, "group": best_group, "stat": stat})
    return pd.DataFrame(rows)


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root = ensure_dirs("06_indicator_species", config)
    out_plots = out_root / "plots"
    out_tables = out_root / "tables"

    check_file(config["paths"]["canonical"]["sp_mat_rds"], "sp_mat", required=True)
    check_file(config["paths"]["canonical"]["env_master_csv"], "env_master", required=True)

    sp_mat = load_pickle(config["paths"]["canonical"]["sp_mat_rds"])
    env = pd.read_csv(config["paths"]["canonical"]["env_master_csv"])

    if isinstance(sp_mat, pd.DataFrame):
        plot_ids = sp_mat.index.astype(str)
        X = sp_mat.to_numpy(dtype=float)
        species_names = sp_mat.columns.astype(str).tolist()
    else:
        X = np.asarray(sp_mat, dtype=float)
        plot_ids = pd.Index([f"plot_{i+1}" for i in range(X.shape[0])])
        species_names = [f"sp_{i+1}" for i in range(X.shape[1])]

    group_col = "forest_type" if "forest_type" in env.columns else "ForTyp" if "ForTyp" in env.columns else None
    if group_col is None:
        raise RuntimeError("No forest grouping column found (forest_type/ForTyp) for indicator species analysis.")

    env_idx = env.set_index("plot_id", drop=False).reindex(plot_ids)
    grp = env_idx[group_col].astype(str).replace("nan", np.nan)
    keep = grp.notna() & (grp != "")

    X_use = X[keep.to_numpy(), :]
    grp_use = grp[keep].to_numpy()

    if len(np.unique(grp_use)) < 2:
        raise RuntimeError("Indicator analysis requires at least two forest groups.")

    ind = _calc_indval(X_use, grp_use, species_names)

    rng = np.random.default_rng(config["params"]["seed"])
    n_perm = int(config["params"]["permutations"])   # use full permutation count (e.g. 999)
    p_vals = []
    for row in ind.itertuples():
        obs = row.stat
        j = species_names.index(row.species_name)
        x = (X_use[:, j] > 0).astype(float)
        count = 0
        for _ in range(n_perm):
            shuf = rng.permutation(grp_use)
            means = [x[shuf == g].mean() if np.any(shuf == g) else 0 for g in np.unique(shuf)]
            if len(means) == 0:
                continue
            mx = max(means)
            A = mx / (sum(means) + 1e-12)
            B = mx
            if A * B >= obs:
                count += 1
        p_vals.append((count + 1) / (n_perm + 1))
    ind["p.value"] = p_vals

    groups = sorted(np.unique(grp_use).tolist())
    for g in groups:
        ind[f"s.{g}"] = (ind["group"] == g).astype(int)

    sig = ind[ind["p.value"] <= 0.05].copy()
    f_main = out_tables / "indicator_species_by_forest_type.csv"
    f_detailed = out_tables / "indicator_species_detailed.csv"
    sig.to_csv(f_detailed, index=False)

    warnings = []
    if len(sig) > 0:
        grp_cols = [c for c in sig.columns if c.startswith("s.")]
        main = sig[["species_name", "stat", "p.value"] + grp_cols].copy()
        long = main.melt(id_vars=["species_name", "stat", "p.value"], var_name="group", value_name="is_indicator")
        long = long[long["is_indicator"] == 1].copy()
        long["group"] = long["group"].str.replace("s.", "", regex=False)
        long = long.sort_values(["group", "stat"], ascending=[True, False])
        long.to_csv(f_main, index=False)

        top = long.groupby("group", group_keys=False).head(5)
        if len(top) > 0:
            pivot = top.pivot(index="species_name", columns="group", values="stat").fillna(0)
            n_sp, n_grp = pivot.shape
            fig_h = max(5, 0.45 * n_sp + 2.5)
            fig_w = max(7, 0.9 * n_grp + 2.5)

            with pub_style(font_size=9):
                fig, ax = plt.subplots(figsize=(fig_w, fig_h))
                im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd",
                               vmin=0, vmax=min(pivot.values.max(), 1.0))

                # Cell value annotations
                for r in range(n_sp):
                    for c in range(n_grp):
                        val = pivot.values[r, c]
                        if val > 0:
                            ax.text(c, r, f"{val:.2f}", ha="center", va="center",
                                    fontsize=7.5,
                                    color="white" if val > 0.5 else "0.2")

                ax.set_yticks(range(n_sp))
                ax.set_yticklabels([f"$\\it{{{sp.replace(' ', '\\ ')}}}$" for sp in pivot.index],
                                   fontsize=8)
                ax.set_xticks(range(n_grp))
                ax.set_xticklabels(pivot.columns, rotation=40, ha="right", fontsize=8.5)
                ax.set_title("Top 5 Indicator Species per Forest Type\n(IndVal statistic, p ≤ 0.05)",
                             pad=10)
                ax.tick_params(axis="both", which="both", length=0)

                # Thin grid lines between cells
                for x_pos in np.arange(-0.5, n_grp, 1):
                    ax.axvline(x_pos, color="white", linewidth=0.8)
                for y_pos in np.arange(-0.5, n_sp, 1):
                    ax.axhline(y_pos, color="white", linewidth=0.8)

                cb = fig.colorbar(im, ax=ax, shrink=0.6, pad=0.02)
                cb.set_label("IndVal", fontsize=9)
                cb.ax.tick_params(labelsize=8)
                ax.set_xlabel("Forest type", labelpad=6)
                ax.set_ylabel("Species", labelpad=6)
                # Turn off grid from pub_style for heatmap
                ax.grid(False)
                fig.tight_layout()
                save_plot(fig, out_plots / "indicator_species_heatmap.png")
    else:
        pd.DataFrame().to_csv(f_main, index=False)
        warnings.append("No significant indicator species at alpha 0.05.")

    return {
        "status": "success",
        "outputs": [str(f_main), str(f_detailed)],
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
