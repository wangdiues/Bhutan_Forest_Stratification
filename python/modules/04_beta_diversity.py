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
        n_init=20,   # ≥20 matches vegan::metaMDS default (Borcard et al. 2018)
        init="random",
        normalized_stress=True,   # stress_ = Kruskal stress-1 (sklearn >= 1.4)
    )
    coords = nmds.fit_transform(bray)
    nmds_scores = pd.DataFrame({"NMDS1": coords[:, 0], "NMDS2": coords[:, 1], "plot_id": plot_ids})
    nmds_scores = nmds_scores.merge(env, on="plot_id", how="left")

    f_scores_csv = out_data / "nmds_scores.csv"
    f_scores_rds = out_data / "nmds_scores.rds"
    f_summary    = out_tables / "analysis_summary.csv"
    f_perm       = out_tables / "permanova_results.txt"
    f_disp       = out_tables / "permdisp_results.txt"
    f_disp_csv   = out_tables / "permdisp_results.csv"
    f_pcoa       = out_plots  / "pcoa_supplementary.png"
    f_pcoa_axes  = out_tables / "pcoa_axis_summary.csv"
    f_mantel     = out_tables / "mantel_test_results.csv"

    nmds_scores.to_csv(f_scores_csv, index=False)
    save_pickle(f_scores_rds, nmds_scores)

    raw_stress = getattr(nmds, "stress_", np.nan)
    kruskal_s1 = _kruskal_stress1(raw_stress, coords)

    # ── 3D NMDS for stress reduction ──────────────────────────────────────────
    # 2D stress ≥ 0.30 is uninterpretable (Kruskal 1964). A 3D solution
    # typically reduces stress substantially; both values are reported.
    kruskal_s1_3d = float("nan")
    try:
        nmds_3d = MDS(
            n_components=3,
            metric_mds=False,
            metric="precomputed",
            random_state=config["params"]["seed"],
            max_iter=300,
            n_init=20,   # ≥20 matches vegan::metaMDS default
            init="random",
            normalized_stress=True,
        )
        coords_3d = nmds_3d.fit_transform(bray)
        raw_stress_3d = getattr(nmds_3d, "stress_", np.nan)
        kruskal_s1_3d = _kruskal_stress1(raw_stress_3d, coords_3d)
        nmds_scores_3d = pd.DataFrame({
            "NMDS1": coords_3d[:, 0],
            "NMDS2": coords_3d[:, 1],
            "NMDS3": coords_3d[:, 2],
            "plot_id": plot_ids,
        })
        nmds_scores_3d.to_csv(out_data / "nmds_scores_3d.csv", index=False)
    except Exception as _exc:
        warnings.append(f"3D NMDS failed: {_exc}")

    summ = pd.DataFrame(
        {
            "metric": ["n_plots", "n_species", "kruskal_stress1_2d", "kruskal_stress1_3d"],
            "value": [X.shape[0], X.shape[1], kruskal_s1, kruskal_s1_3d],
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

    # Update summary with PERMANOVA results (R² stored to 4 dp for consistency)
    summ = pd.concat([
        summ,
        pd.DataFrame({
            "metric": ["permanova_pseudo_f", "permanova_p", "permanova_r2",
                       "permanova_n_groups", "permanova_n_samples"],
            "value": [round(pseudo_f, 4), round(perm_p, 6), round(perm_r2, 4),
                      n_groups, n_perm_samples],
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
            if np.isfinite(kruskal_s1_3d):
                stress_str = (f"Kruskal stress-1 (2D) = {kruskal_s1:.4f}\n"
                              f"Kruskal stress-1 (3D) = {kruskal_s1_3d:.4f}")
            else:
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

    # ── PERMDISP2: Anderson (2006) permutation-based F-test on dispersions ────
    # Replaces the previous K-W proxy. Tests H₀: all groups have equal
    # multivariate dispersion (spread around centroid in PCoA space).
    try:
        from skbio.stats.ordination import pcoa as _pcoa
        from skbio import DistanceMatrix as _DM2

        rng_disp  = np.random.default_rng(config["params"]["seed"])
        grp_arr   = np.array(grp)
        dm_arr    = bray[np.ix_(keep.to_numpy(), keep.to_numpy())]
        groups_u  = np.unique(grp_arr)

        # Compute PCoA from Bray-Curtis distance matrix
        pc = _pcoa(_DM2(dm_arr))
        coords_pc = pc.samples.values  # (n, n_axes)

        # Distance of each plot to its group centroid in PCoA space
        d_to_centroid = np.zeros(len(grp_arr))
        group_disp = {}
        for g in groups_u:
            mask_g = (grp_arr == g)
            if mask_g.sum() < 2:
                d_to_centroid[mask_g] = np.nan
                continue
            centroid = coords_pc[mask_g].mean(axis=0)
            dists = np.linalg.norm(coords_pc[mask_g] - centroid, axis=1)
            d_to_centroid[mask_g] = dists
            group_disp[g] = round(float(dists.mean()), 4)

        valid_mask = np.isfinite(d_to_centroid)
        valid_d    = d_to_centroid[valid_mask]
        valid_g    = grp_arr[valid_mask]
        active_grps = [g for g in groups_u if (valid_g == g).sum() >= 2]

        def _f_stat(d, g):
            grand_mean = d.mean()
            k = len(np.unique(g))
            n = len(d)
            ss_b = sum(
                (g == grp_g).sum() * (d[g == grp_g].mean() - grand_mean) ** 2
                for grp_g in np.unique(g)
            )
            ss_w = sum(
                ((d[g == grp_g] - d[g == grp_g].mean()) ** 2).sum()
                for grp_g in np.unique(g)
            )
            if ss_w == 0 or n - k <= 0:
                return float("nan")
            return (ss_b / (k - 1)) / (ss_w / (n - k))

        if len(active_grps) >= 2:
            f_obs = _f_stat(valid_d, valid_g)
            n_perm_disp = int(config["params"].get("permutations", 999))
            f_null = [
                _f_stat(valid_d, rng_disp.permutation(valid_g))
                for _ in range(n_perm_disp)
            ]
            f_null_arr = np.array([x for x in f_null if np.isfinite(x)])
            p_disp = float((np.sum(f_null_arr >= f_obs) + 1) / (len(f_null_arr) + 1))

            disp_lines = [
                "PERMDISP2 — Anderson (2006) Homogeneity of Multivariate Dispersion",
                "=" * 60,
                "Method: Permutation-based F-test on PCoA centroid distances",
                f"  F statistic      : {f_obs:.4f}",
                f"  p-value          : {p_disp:.4f}",
                f"  n permutations   : {n_perm_disp}",
                f"  n groups         : {len(active_grps)}",
                "",
                "Group-level mean dispersion (distance to PCoA centroid):",
            ] + [f"  {g}: {v}" for g, v in group_disp.items()] + [
                "",
                "Interpretation:",
                (
                    "  Significant (p ≤ 0.05): groups differ in dispersion. "
                    "PERMANOVA R² may partly reflect dispersion, not only location."
                    if p_disp <= 0.05
                    else
                    "  Non-significant (p > 0.05): no evidence of unequal dispersions. "
                    "PERMANOVA reflects compositional location differences."
                ),
            ]
            existing = f_perm.read_text(encoding="utf-8")
            f_perm.write_text(existing + "\n\n" + "\n".join(disp_lines) + "\n",
                              encoding="utf-8")
            f_disp.write_text("\n".join(disp_lines) + "\n", encoding="utf-8")
            # Save CSV summary
            disp_rows = [{"group": g, "mean_dispersion": v}
                         for g, v in group_disp.items()]
            disp_rows.append({"group": "PERMDISP2_F", "mean_dispersion": round(f_obs, 4)})
            disp_rows.append({"group": "PERMDISP2_p", "mean_dispersion": round(p_disp, 4)})
            pd.DataFrame(disp_rows).to_csv(f_disp_csv, index=False)
            summ = pd.concat([
                summ,
                pd.DataFrame({
                    "metric": ["permdisp2_F", "permdisp2_p"],
                    "value":  [round(f_obs, 4), round(p_disp, 6)],
                }),
            ], ignore_index=True)
            summ.to_csv(f_summary, index=False)
        else:
            f_disp.write_text("PERMDISP2 skipped: too few groups with ≥ 2 plots.\n",
                              encoding="utf-8")
    except Exception as exc:
        warnings.append(f"PERMDISP2 failed: {type(exc).__name__}: {exc}")
        f_disp.write_text(f"PERMDISP2 failed: {exc}\n", encoding="utf-8")

    # ── B1: Mantel test — compositional vs geographic distance ────────────────
    f_mantel = out_tables / "mantel_test_results.csv"
    try:
        from skbio.stats.distance import mantel as _mantel, DistanceMatrix as _DMm
        from sklearn.metrics.pairwise import haversine_distances as _hav_dist

        coord_cols = [c for c in ["latitude", "longitude"] if c in env.columns]
        if len(coord_cols) == 2 and "plot_id" in env.columns:
            env_coord = (env.set_index("plot_id")
                           .reindex(labels)[coord_cols]
                           .dropna())
            shared_ids = [i for i in labels if i in env_coord.index]
            if len(shared_ids) >= 10:
                geo_idx = [labels.index(i) for i in shared_ids]
                coords_rad = np.deg2rad(
                    env_coord.loc[shared_ids, ["latitude", "longitude"]].values
                )
                # Haversine distances (km) via sklearn (scipy pdist lacks haversine)
                geo_dist = _hav_dist(coords_rad) * 6371.0
                bc_sub = bray[np.ix_(keep.to_numpy(), keep.to_numpy())]
                bc_shared = bc_sub[np.ix_(geo_idx, geo_idx)]
                dm_bc  = _DMm(bc_shared, ids=shared_ids)
                dm_geo = _DMm(geo_dist,  ids=shared_ids)
                r_m, p_m, n_m = _mantel(
                    dm_bc, dm_geo, method="pearson",
                    permutations=int(config["params"].get("permutations", 999))
                )
                pd.DataFrame([{
                    "mantel_r":      round(float(r_m), 4),
                    "p_value":       round(float(p_m), 4),
                    "n_permutations": int(n_m),
                    "n_plots":       len(shared_ids),
                    "method":        "Pearson",
                    "matrices":      "Bray-Curtis vs Haversine geographic distance (km)",
                }]).to_csv(f_mantel, index=False)
                summ = pd.concat([
                    summ,
                    pd.DataFrame({
                        "metric": ["mantel_r", "mantel_p"],
                        "value":  [round(float(r_m), 4), round(float(p_m), 4)],
                    }),
                ], ignore_index=True)
                summ.to_csv(f_summary, index=False)
            else:
                warnings.append("Mantel test skipped: insufficient shared plot coordinates.")
        else:
            warnings.append("Mantel test skipped: latitude/longitude missing from env_master.")
    except Exception as exc:
        warnings.append(f"Mantel test failed: {type(exc).__name__}: {exc}")

    # ── ANOSIM robustness check ───────────────────────────────────────────────
    # ANOSIM R is less sensitive to dispersion heterogeneity than PERMANOVA
    # and provides a complementary test of between-group separation.
    try:
        from skbio.stats.distance import anosim as _anosim
        anosim_result = _anosim(dm, grouping=grp,
                                permutations=config["params"]["permutations"])
        anosim_r = float(anosim_result["test statistic"])
        anosim_p = float(anosim_result["p-value"])
        anosim_text = (
            f"\n\nANOSIM Robustness Check\n"
            f"{'=' * 45}\n"
            f"  R statistic : {anosim_r:.4f}\n"
            f"  p-value     : {anosim_p:.4f}\n"
            f"  Permutations: {config['params']['permutations']}\n"
            f"  Interpretation: R > 0.25 suggests meaningful separation; "
            f"R near 0 = groups indistinguishable.\n"
        )
        existing_perm = f_perm.read_text(encoding="utf-8")
        f_perm.write_text(existing_perm + anosim_text, encoding="utf-8")
        summ = pd.concat([
            summ,
            pd.DataFrame({
                "metric": ["anosim_r", "anosim_p"],
                "value":  [round(anosim_r, 4), round(anosim_p, 6)],
            }),
        ], ignore_index=True)
        summ.to_csv(f_summary, index=False)
    except Exception as exc:
        warnings.append(f"ANOSIM failed: {type(exc).__name__}: {exc}")

    # ── PCoA supplementary figure ─────────────────────────────────────────────
    # Principal Coordinates Analysis (PCoA / Classical MDS) is a metric
    # ordination that faithfully represents Bray-Curtis distances better than
    # 2D NMDS when stress is high (Kruskal stress-1 = 0.338 here).
    # Provided as Supplementary Figure S1b for reviewer transparency.
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
        pct_var = eigenvalues / var_total * 100 if var_total > 0 else np.zeros(len(eigenvalues))
        pct1 = float(pct_var[0])
        pct2 = float(pct_var[1])

        # Write PCoA axis summary table (A11)
        f_pcoa_axes = out_tables / "pcoa_axis_summary.csv"
        pd.DataFrame({
            "axis": [f"PCoA{i+1}" for i in range(len(pct_var))],
            "pct_total_variation": [round(p, 2) for p in pct_var],
        }).to_csv(f_pcoa_axes, index=False)

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
            ax2.set_xlabel("PCoA1")
            ax2.set_ylabel("PCoA2")
            ax2.set_title(
                "PCoA Ordination of Plot Species Composition\n"
                "(Bray–Curtis dissimilarity; metric ordination, Supplementary)"
            )
            fig2.tight_layout()
            save_plot(fig2, f_pcoa)
    except Exception as exc:
        warnings.append(f"PCoA supplementary figure failed: {type(exc).__name__}: {exc}")

    return {
        "status": "success",
        "outputs": [str(f_scores_csv), str(f_scores_rds), str(f_summary),
                    str(f_perm), str(f_disp), str(f_disp_csv), str(f_pcoa),
                    str(f_pcoa_axes), str(f_mantel)],
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
