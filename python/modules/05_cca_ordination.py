from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cross_decomposition import CCA

from python.utils import FOREST_PALETTE, check_file, ensure_dirs, load_pickle, pub_style, save_pickle, save_plot


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root = ensure_dirs("05_cca_ordination", config)
    out_plots = out_root / "plots"
    out_tables = out_root / "tables"
    out_models = out_root / "models"

    check_file(config["paths"]["canonical"]["sp_mat_rds"], "sp_mat", required=True)
    check_file(config["paths"]["canonical"]["env_master_csv"], "env_master", required=True)

    sp_mat = load_pickle(config["paths"]["canonical"]["sp_mat_rds"])
    env = pd.read_csv(config["paths"]["canonical"]["env_master_csv"])

    if isinstance(sp_mat, pd.DataFrame):
        plot_ids = sp_mat.index.astype(str)
        species_names = sp_mat.columns.astype(str).tolist()
        X_species = sp_mat.to_numpy(dtype=float)
    else:
        X_species = np.asarray(sp_mat, dtype=float)
        plot_ids = pd.Index([f"plot_{i+1}" for i in range(X_species.shape[0])])
        species_names = [f"sp_{i+1}" for i in range(X_species.shape[1])]

    env = env.set_index("plot_id", drop=False).reindex(plot_ids).reset_index(drop=True)

    # Warn when plots in sp_mat have no matching row in env_master (silent NaN inflation)
    missing_env = int(env["plot_id"].isna().sum()) if "plot_id" in env.columns else 0
    warnings_list: list[str] = []
    if missing_env > 0:
        warnings_list.append(
            f"{missing_env} plot(s) from sp_mat have no matching row in env_master; "
            "their environmental variables are NaN and will be imputed by median."
        )

    num_vars = [c for c in env.columns if pd.api.types.is_numeric_dtype(env[c])]
    num_vars = [c for c in num_vars if c not in {"longitude", "latitude", "forest_raster_value", "area_ha"}]

    usable = []
    for c in num_vars:
        s = pd.to_numeric(env[c], errors="coerce")
        if s.isna().mean() < 0.5 and s.std(skipna=True) > 0:
            usable.append(c)

    if not usable:
        raise RuntimeError("No usable numeric environmental predictors for CCA.")

    X_env = env[usable].apply(pd.to_numeric, errors="coerce")
    X_env = X_env.fillna(X_env.median(numeric_only=True))

    # Limit species to the top-200 most frequent to keep CCA tractable in memory
    MAX_SPECIES = 200
    occ_counts = (X_species > 0).sum(axis=0)
    if X_species.shape[1] > MAX_SPECIES:
        top_idx = np.argsort(occ_counts)[::-1][:MAX_SPECIES]
        X_species = X_species[:, top_idx]
        species_names = [species_names[i] for i in top_idx]

    n_comp = min(2, X_env.shape[1], X_species.shape[1])
    cca = CCA(n_components=n_comp)
    Y = X_species
    X_c, Y_c = cca.fit(X_env, Y).transform(X_env, Y)

    f_model = out_models / "cca_model.rds"
    f_anova = out_tables / "cca_anova.txt"
    f_site = out_tables / "cca_site_scores.csv"
    f_species = out_tables / "cca_species_scores.csv"
    f_env = out_tables / "cca_env_biplot_scores.csv"

    save_pickle(f_model, cca)
    f_anova.write_text("Permutation ANOVA for CCA is not implemented in this Python port.\n", encoding="utf-8")

    site_scores = pd.DataFrame({"plot_id": plot_ids, "CCA1": X_c[:, 0]})
    if n_comp > 1:
        site_scores["CCA2"] = X_c[:, 1]
    species_scores = pd.DataFrame({"species_name": species_names, "CCA1": cca.y_weights_[:, 0]})
    if n_comp > 1:
        species_scores["CCA2"] = cca.y_weights_[:, 1]
    env_scores = pd.DataFrame({"variable": usable, "CCA1": cca.x_weights_[:, 0]})
    if n_comp > 1:
        env_scores["CCA2"] = cca.x_weights_[:, 1]

    site_scores.to_csv(f_site, index=False)
    species_scores.to_csv(f_species, index=False)
    env_scores.to_csv(f_env, index=False)

    if {"CCA1", "CCA2"}.issubset(site_scores.columns):
        # Normalise site scores to [-1, 1] independently per axis
        s1 = site_scores["CCA1"].to_numpy(dtype=float)
        s2 = site_scores["CCA2"].to_numpy(dtype=float)
        s1_scale = max(np.abs(s1).max(), 1e-12)
        s2_scale = max(np.abs(s2).max(), 1e-12)
        s1_n = s1 / s1_scale
        s2_n = s2 / s2_scale

        # Scale env arrows independently, then cap to 0.85 of plot range
        if "CCA1" in env_scores.columns and "CCA2" in env_scores.columns:
            raw_e1 = env_scores["CCA1"].to_numpy(dtype=float)
            raw_e2 = env_scores["CCA2"].to_numpy(dtype=float)
            e_scale = max(np.sqrt(raw_e1**2 + raw_e2**2).max(), 1e-12)
            env_s1 = raw_e1 / e_scale * 0.85
            env_s2 = raw_e2 / e_scale * 0.85
        else:
            env_s1 = env_s2 = None

        # Merge forest_type for colouring
        ft_col = None
        if "forest_type" in env.columns:
            ft_col = env["forest_type"].astype(str).tolist()
        elif "ForTyp" in env.columns:
            ft_col = env["ForTyp"].astype(str).tolist()

        with pub_style():
            fig, ax = plt.subplots(figsize=(7, 6))

            if ft_col is not None:
                unique_fts = sorted(set(ft_col))
                cmap = {ft: FOREST_PALETTE[i % len(FOREST_PALETTE)] for i, ft in enumerate(unique_fts)}
                for ft in unique_fts:
                    idx = [i for i, v in enumerate(ft_col) if v == ft]
                    ax.scatter(s1_n[idx], s2_n[idx], color=cmap[ft],
                               s=16, alpha=0.55, linewidths=0, label=ft, rasterized=True)
                leg = ax.legend(title="Forest type", bbox_to_anchor=(1.01, 1), loc="upper left",
                                framealpha=0.9, edgecolor="0.8", ncol=1, fontsize=8)
            else:
                ax.scatter(s1_n, s2_n, color=FOREST_PALETTE[0],
                           s=16, alpha=0.55, linewidths=0, rasterized=True)

            # Environment biplot arrows
            if env_s1 is not None and env_s2 is not None:
                arrow_scale = 0.85
                for i, var in enumerate(env_scores["variable"]):
                    ax.annotate(
                        "", xy=(env_s1[i] * arrow_scale, env_s2[i] * arrow_scale), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color="#E15759", lw=1.2),
                    )
                    ax.text(env_s1[i] * (arrow_scale + 0.08), env_s2[i] * (arrow_scale + 0.08),
                            var, color="#E15759", fontsize=8, ha="center", va="center",
                            bbox=dict(fc="white", ec="none", alpha=0.7, pad=1))

            # Reference axes
            ax.axhline(0, color="0.6", linewidth=0.6, zorder=0)
            ax.axvline(0, color="0.6", linewidth=0.6, zorder=0)
            ax.set_xlabel("CCA1 (normalised)")
            ax.set_ylabel("CCA2 (normalised)")
            ax.set_title("CCA Site Scores with Environmental Vectors")
            ax.set_xlim(-1.15, 1.15)
            ax.set_ylim(-1.15, 1.15)
            fig.subplots_adjust(right=0.72)
            save_plot(fig, out_plots / "cca_sites.png")

    return {
        "status": "success",
        "outputs": [str(f_model), str(f_anova), str(f_site), str(f_species), str(f_env)],
        "warnings": warnings_list,
        "runtime_sec": time.time() - t0,
    }
