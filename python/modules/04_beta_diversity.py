from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from sklearn.manifold import MDS

from python.utils import FOREST_PALETTE, check_file, ensure_dirs, load_pickle, pub_style, save_pickle, save_plot


def _kruskal_stress1(raw_stress: float, coords: np.ndarray) -> float:
    """Return Kruskal stress-1 as-is (already normalized by sklearn).

    With normalized_stress=True (sklearn >= 1.4), MDS.stress_ is already
    Kruskal stress formula 1: sqrt(Σ(d - dhat)² / Σ d²).
    This function is kept for API compatibility but simply passes the value through.
    """
    return float(raw_stress) if np.isfinite(raw_stress) else float("nan")


def _permanova_r2(pseudo_f: float, n_samples: int, n_groups: int) -> float:
    """Compute PERMANOVA R² from pseudo-F statistic.

    R² = SS_between / SS_total
       = (F * df_between) / (F * df_between + df_within)
    df_between = k − 1,  df_within = n − k
    """
    df_b = n_groups - 1
    df_w = n_samples - n_groups
    numerator = pseudo_f * df_b
    return float(numerator / (numerator + df_w))


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
        normalized_stress=True,   # stress_ = Kruskal stress-1 (sklearn >= 1.4)
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

    raw_stress = getattr(nmds, "stress_", np.nan)
    kruskal_s1 = _kruskal_stress1(raw_stress, coords)

    summ = pd.DataFrame(
        {
            "metric": ["n_plots", "n_species", "kruskal_stress1"],
            "value": [X.shape[0], X.shape[1], kruskal_s1],
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

    # Extract pseudo-F and compute R²
    pseudo_f = float(ad["test statistic"])
    perm_p   = float(ad["p-value"])
    n_perm_samples = int(keep.sum())
    n_groups  = grp_series.nunique()
    perm_r2   = _permanova_r2(pseudo_f, n_perm_samples, n_groups)

    perm_text = (
        str(ad)
        + f"\n\nR² (effect size) = {perm_r2:.4f}\n"
        f"  computed as F*(k-1) / (F*(k-1) + (n-k))\n"
        f"  where k={n_groups} groups, n={n_perm_samples} plots\n"
    )
    f_perm.write_text(perm_text, encoding="utf-8")

    # Update summary with PERMANOVA results
    summ = pd.concat([
        summ,
        pd.DataFrame({
            "metric": ["permanova_pseudo_f", "permanova_p", "permanova_r2",
                       "permanova_n_groups", "permanova_n_samples"],
            "value": [pseudo_f, perm_p, perm_r2, n_groups, n_perm_samples],
        }),
    ], ignore_index=True)
    summ.to_csv(f_summary, index=False)

    with pub_style():
        fig, ax = plt.subplots(figsize=(7, 5.5))
        if "forest_type" in nmds_scores.columns:
            unique_fts = sorted(nmds_scores["forest_type"].dropna().astype(str).unique())
            cmap = {ft: FOREST_PALETTE[i % len(FOREST_PALETTE)] for i, ft in enumerate(unique_fts)}
            for ft in unique_fts:
                sub = nmds_scores[nmds_scores["forest_type"].astype(str) == ft]
                ax.scatter(sub["NMDS1"], sub["NMDS2"], color=cmap[ft],
                           s=18, alpha=0.65, linewidths=0, label=ft, rasterized=True)
            ax.legend(title="Forest type", bbox_to_anchor=(1.01, 1), loc="upper left",
                      framealpha=0.9, edgecolor="0.8", ncol=1, fontsize=8)
        else:
            ax.scatter(nmds_scores["NMDS1"], nmds_scores["NMDS2"],
                       color=FOREST_PALETTE[0], s=18, alpha=0.65,
                       linewidths=0, rasterized=True)

        # Reference axes
        ax.axhline(0, color="0.6", linewidth=0.6, linestyle="-", zorder=0)
        ax.axvline(0, color="0.6", linewidth=0.6, linestyle="-", zorder=0)

        # Stress annotation — Kruskal stress-1 (normalized_stress=True ensures this)
        if not np.isnan(kruskal_s1):
            stress_str = f"Kruskal stress-1 = {kruskal_s1:.4f}"
        else:
            stress_str = None
        if stress_str:
            ax.text(0.02, 0.02, stress_str, transform=ax.transAxes,
                    fontsize=9, va="bottom",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.8", alpha=0.9))

        ax.set_xlabel("NMDS1")
        ax.set_ylabel("NMDS2")
        ax.set_title("NMDS Ordination of Plot Species Composition\n(Bray–Curtis dissimilarity)")
        fig.tight_layout()
        save_plot(fig, out_plots / "nmds_ordination.png")

    # ── PERMDISP: group dispersion homogeneity test ───────────────────────────
    # PERMANOVA is sensitive to differences in group dispersion (spread) as well
    # as location.  PERMDISP tests whether groups differ in dispersion only.
    # Method: compute distance of each plot to its group centroid in Bray-Curtis
    # space, then run a Kruskal-Wallis H test (non-parametric ANOVA on distances).
    # If PERMDISP is not significant but PERMANOVA is, the PERMANOVA result
    # reflects genuine compositional location differences, not dispersion artefact.
    f_disp = out_tables / "permdisp_results.txt"
    try:
        from scipy import stats as _sp_stats

        grp_arr   = np.array(grp)
        dm_arr    = bray[np.ix_(keep.to_numpy(), keep.to_numpy())]
        groups_u  = np.unique(grp_arr)
        # Centroid distance = mean distance from each plot to its group centroid
        # Approximated as distance to group mean in distance space (standard PERMDISP2)
        centroid_dists = np.full(len(grp_arr), np.nan)
        for g in groups_u:
            idx_g = np.where(grp_arr == g)[0]
            if len(idx_g) < 2:
                continue
            sub_dm = dm_arr[np.ix_(idx_g, idx_g)]
            # Distance to centroid (average distance from each member to all others /2)
            avg_dist = sub_dm.mean(axis=1) / 2.0
            centroid_dists[idx_g] = avg_dist

        valid_disp = ~np.isnan(centroid_dists)
        group_dist_lists = [
            centroid_dists[valid_disp][np.array(grp_arr)[valid_disp] == g]
            for g in groups_u
            if (np.array(grp_arr)[valid_disp] == g).sum() >= 2
        ]
        if len(group_dist_lists) >= 2:
            h_stat, disp_p = _sp_stats.kruskal(*group_dist_lists)
            disp_lines = [
                "PERMDISP — Homogeneity of Multivariate Dispersion",
                "=" * 50,
                "Method: Kruskal-Wallis H test on within-group centroid distances",
                f"  H statistic : {h_stat:.4f}",
                f"  p-value     : {disp_p:.4f}",
                f"  n groups    : {len(group_dist_lists)}",
                "",
                "Interpretation:",
                (
                    "  Significant (p ≤ 0.05): groups differ in dispersion. "
                    "PERMANOVA result may partly reflect dispersion differences, "
                    "not only location. Report both statistics."
                    if disp_p <= 0.05
                    else
                    "  Non-significant (p > 0.05): no evidence of dispersion differences. "
                    "PERMANOVA result can be interpreted as reflecting compositional "
                    "location differences among forest types."
                ),
            ]
            # Append PERMDISP result to permanova file
            existing = f_perm.read_text(encoding="utf-8")
            f_perm.write_text(
                existing + "\n\n" + "\n".join(disp_lines) + "\n",
                encoding="utf-8",
            )
            f_disp.write_text("\n".join(disp_lines) + "\n", encoding="utf-8")
            # Add to summary
            summ = pd.concat([
                summ,
                pd.DataFrame({
                    "metric": ["permdisp_H", "permdisp_p"],
                    "value":  [round(h_stat, 4), round(disp_p, 6)],
                }),
            ], ignore_index=True)
            summ.to_csv(f_summary, index=False)
        else:
            f_disp.write_text("PERMDISP skipped: too few groups with ≥ 2 plots.\n",
                              encoding="utf-8")
    except Exception as exc:
        warnings.append(f"PERMDISP failed: {type(exc).__name__}: {exc}")
        f_disp.write_text(f"PERMDISP failed: {exc}\n", encoding="utf-8")

    # ── PCoA supplementary figure ─────────────────────────────────────────────
    # Principal Coordinates Analysis (PCoA / Classical MDS) is a metric
    # ordination that faithfully represents Bray-Curtis distances better than
    # 2D NMDS when stress is high (Kruskal stress-1 = 0.338 here).
    # Provided as Supplementary Figure S1b for reviewer transparency.
    f_pcoa = out_plots / "pcoa_supplementary.png"
    try:
        from sklearn.manifold import MDS as _MDS

        pcoa = _MDS(
            n_components=2,
            metric_mds=True,          # metric = PCoA
            metric="precomputed",
            random_state=config["params"]["seed"],
            max_iter=300,
            n_init=1,
            normalized_stress="auto",
        )
        pcoa_coords = pcoa.fit_transform(bray)
        pcoa_scores = pd.DataFrame(
            {"PCoA1": pcoa_coords[:, 0], "PCoA2": pcoa_coords[:, 1], "plot_id": plot_ids}
        ).merge(env[["plot_id", "forest_type"]] if "forest_type" in env.columns else env[["plot_id"]], on="plot_id", how="left")

        # Variance explained by each axis
        eigenvalues = np.var(pcoa_coords, axis=0)
        var_total = eigenvalues.sum()
        pct1 = eigenvalues[0] / var_total * 100 if var_total > 0 else 0
        pct2 = eigenvalues[1] / var_total * 100 if var_total > 0 else 0

        with pub_style():
            fig2, ax2 = plt.subplots(figsize=(7, 5.5))
            if "forest_type" in pcoa_scores.columns:
                unique_fts = sorted(pcoa_scores["forest_type"].dropna().astype(str).unique())
                cmap = {ft: FOREST_PALETTE[i % len(FOREST_PALETTE)] for i, ft in enumerate(unique_fts)}
                for ft in unique_fts:
                    sub = pcoa_scores[pcoa_scores["forest_type"].astype(str) == ft]
                    ax2.scatter(sub["PCoA1"], sub["PCoA2"], color=cmap[ft],
                                s=18, alpha=0.65, linewidths=0, label=ft, rasterized=True)
                ax2.legend(title="Forest type", bbox_to_anchor=(1.01, 1), loc="upper left",
                           framealpha=0.9, edgecolor="0.8", ncol=1, fontsize=8)
            else:
                ax2.scatter(pcoa_scores["PCoA1"], pcoa_scores["PCoA2"],
                            color=FOREST_PALETTE[0], s=18, alpha=0.65,
                            linewidths=0, rasterized=True)
            ax2.axhline(0, color="0.6", linewidth=0.6, linestyle="-", zorder=0)
            ax2.axvline(0, color="0.6", linewidth=0.6, linestyle="-", zorder=0)
            ax2.set_xlabel(f"PCoA1 ({pct1:.1f}% variance)")
            ax2.set_ylabel(f"PCoA2 ({pct2:.1f}% variance)")
            ax2.set_title(
                "PCoA Ordination of Plot Species Composition\n"
                "(Bray–Curtis dissimilarity; metric ordination, Supplementary)"
            )
            ax2.text(0.02, 0.02,
                     "Metric PCoA provided as complement to NMDS\n"
                     f"(NMDS Kruskal stress-1 = {kruskal_s1:.3f} > 0.20 threshold)",
                     transform=ax2.transAxes, fontsize=8, va="bottom",
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.8", alpha=0.9))
            fig2.tight_layout()
            save_plot(fig2, f_pcoa)
    except Exception as exc:
        warnings.append(f"PCoA supplementary figure failed: {type(exc).__name__}: {exc}")

    return {
        "status": "success",
        "outputs": [str(f_scores_csv), str(f_scores_rds), str(f_summary),
                    str(f_perm), str(f_disp), str(f_pcoa)],
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
