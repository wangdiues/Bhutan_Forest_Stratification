from __future__ import annotations

import time

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for thread-safe parallel execution
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from utils import check_file, ensure_dirs, load_pickle, save_plot
except ImportError:
    from python.utils import check_file, ensure_dirs, load_pickle, save_plot


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
    n_perm = min(199, int(config["params"]["permutations"]))
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

        top = long.groupby("group", group_keys=False).head(10)
        if len(top) > 0:
            pivot = top.pivot(index="species_name", columns="group", values="stat").fillna(0)
            fig, ax = plt.subplots(figsize=(10, 8))
            im = ax.imshow(pivot.values, aspect="auto")
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index)
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
            ax.set_title("Top indicator species by group")
            fig.colorbar(im, ax=ax, label="IndVal")
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
