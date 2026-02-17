from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from sklearn.manifold import MDS

try:
    from utils import check_file, ensure_dirs, load_pickle, save_pickle, save_plot
except ImportError:
    from python.utils import check_file, ensure_dirs, load_pickle, save_pickle, save_plot


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root = ensure_dirs("04_beta_diversity", config)
    out_plots = out_root / "plots"
    out_tables = out_root / "tables"
    out_data = out_root / "data"

    check_file(config["paths"]["canonical"]["sp_mat_rds"], "sp_mat", required=True)
    check_file(config["paths"]["canonical"]["env_master_csv"], "env_master", required=True)
    warnings = []

    sp_mat = load_pickle(config["paths"]["canonical"]["sp_mat_rds"])
    if isinstance(sp_mat, pd.DataFrame):
        plot_ids = sp_mat.index.astype(str)
        X = sp_mat.to_numpy(dtype=float)
    else:
        X = np.asarray(sp_mat, dtype=float)
        plot_ids = pd.Index([f"plot_{i+1}" for i in range(X.shape[0])])

    env = pd.read_csv(config["paths"]["canonical"]["env_master_csv"])

    if X.shape[0] < 2 or X.shape[1] < 2:
        raise RuntimeError("Species matrix too small for beta-diversity analysis.")

    bray = squareform(pdist(X, metric="braycurtis"))

    nmds = MDS(
        n_components=2,
        metric_mds=False,
        metric="precomputed",
        random_state=config["params"]["seed"],
        max_iter=300,
        n_init=4,
        init="random",
    )
    coords = nmds.fit_transform(bray)
    nmds_scores = pd.DataFrame({"NMDS1": coords[:, 0], "NMDS2": coords[:, 1], "plot_id": plot_ids})
    nmds_scores = nmds_scores.merge(env, on="plot_id", how="left")

    f_scores_csv = out_data / "nmds_scores.csv"
    f_scores_rds = out_data / "nmds_scores.rds"
    f_summary = out_tables / "analysis_summary.csv"
    f_perm = out_tables / "permanova_results.txt"

    nmds_scores.to_csv(f_scores_csv, index=False)
    save_pickle(f_scores_rds, nmds_scores)

    summ = pd.DataFrame(
        {
            "metric": ["n_plots", "n_species", "nmds_stress"],
            "value": [X.shape[0], X.shape[1], getattr(nmds, "stress_", np.nan)],
        }
    )
    summ.to_csv(f_summary, index=False)

    try:
        from skbio import DistanceMatrix
        from skbio.stats.distance import permanova
    except Exception as exc:
        raise RuntimeError(
            "PERMANOVA is required for module 04 but scikit-bio is not available."
        ) from exc

    if "forest_type" not in nmds_scores.columns:
        raise RuntimeError(
            "PERMANOVA is required for module 04, but 'forest_type' is missing in env_master."
        )

    keep = nmds_scores["forest_type"].notna()
    if int(keep.sum()) < 2:
        raise RuntimeError(
            "PERMANOVA is required for module 04, but there are fewer than 2 non-null forest_type rows."
        )

    grp_series = nmds_scores.loc[keep, "forest_type"].astype(str)
    if grp_series.nunique() < 2:
        raise RuntimeError(
            "PERMANOVA is required for module 04, but fewer than 2 forest_type groups are present."
        )

    labels = nmds_scores.loc[keep, "plot_id"].astype(str).tolist()
    dm = DistanceMatrix(bray[np.ix_(keep.to_numpy(), keep.to_numpy())], ids=labels)
    grp = grp_series.tolist()
    ad = permanova(dm, grouping=grp, permutations=config["params"]["permutations"])
    perm_text = str(ad)
    f_perm.write_text(perm_text + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(8, 6))
    if "forest_type" in nmds_scores.columns:
        for grp, sub in nmds_scores.groupby("forest_type", dropna=False):
            ax.scatter(sub["NMDS1"], sub["NMDS2"], alpha=0.7, label=str(grp))
        ax.legend(title="forest_type", fontsize=8)
    else:
        ax.scatter(nmds_scores["NMDS1"], nmds_scores["NMDS2"], alpha=0.7)
    ax.set_title("NMDS ordination")
    ax.set_xlabel("NMDS1")
    ax.set_ylabel("NMDS2")
    save_plot(fig, out_plots / "nmds_ordination.png")

    return {
        "status": "success",
        "outputs": [str(f_scores_csv), str(f_scores_rds), str(f_summary), str(f_perm)],
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
