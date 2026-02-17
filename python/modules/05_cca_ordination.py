from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cross_decomposition import CCA

try:
    from utils import check_file, ensure_dirs, load_pickle, save_pickle, save_plot
except ImportError:
    from python.utils import check_file, ensure_dirs, load_pickle, save_pickle, save_plot


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
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(site_scores["CCA1"], site_scores["CCA2"], alpha=0.7)
        ax.set_title("CCA site scores")
        ax.set_xlabel("CCA1")
        ax.set_ylabel("CCA2")
        save_plot(fig, out_plots / "cca_sites.png")

    return {
        "status": "success",
        "outputs": [str(f_model), str(f_anova), str(f_site), str(f_species), str(f_env)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
