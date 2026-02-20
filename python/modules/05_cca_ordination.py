"""05_cca_ordination — Canonical Correspondence Analysis (ecological CCA).

Method: skbio.stats.ordination.cca — chi-square constrained ordination
(ter Braak 1986), NOT sklearn CCA (cross-decomposition/PLS variant).

Outputs:
  tables/
    cca_site_scores.csv          — sample (plot) scores on CCA axes
    cca_species_scores.csv       — species scores on CCA axes
    cca_env_biplot_scores.csv    — env variable biplot arrow coordinates
    cca_variance_explained.csv   — eigenvalues + proportion explained per axis
    cca_permutation_test.csv     — axis permutation test (p-value vs null)
    variance_partitioning.csv    — adj-R² by variable group (Borcard 1992)
    cca_anova.txt                — axis test summary text
  plots/
    cca_sites.png                — triplot: sites coloured by forest type
"""
from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from python.utils import FOREST_PALETTE, check_file, ensure_dirs, load_pickle, pub_style, save_pickle, save_plot

# Columns that must never enter the constrained ordination
# (spatial surrogates, synthetic proxies, identifiers, and known duplicates)
_EXCLUDE_FROM_ORDINATION = {
    "longitude", "latitude", "forest_raster_value", "area_ha",
    "lat_elevation_proxy", "dist_from_center",           # synthetic proxies (module 02)
    "plot_id", "forest_type", "soil_type", "stratum",    # categorical / identifiers
}


def _mean_r2(Y: np.ndarray, X: np.ndarray) -> float:
    """Mean adjusted R² across species from OLS(Y ~ X).

    Approximates constrained inertia for variance partitioning
    (Borcard et al. 1992).  Only species with non-zero variance included.
    """
    n, p = X.shape
    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)
    r2_vals = []
    for j in range(Y.shape[1]):
        y = Y[:, j].astype(float)
        if y.std() < 1e-9:
            continue
        lr = LinearRegression(fit_intercept=True).fit(X_s, y)
        ss_res = float(np.sum((y - lr.predict(X_s)) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot
        r2_adj = (1.0 - (1.0 - r2) * (n - 1) / (n - p - 1)
                  if n - p - 1 > 0 else r2)
        r2_vals.append(r2_adj)
    return float(np.mean(r2_vals)) if r2_vals else float("nan")


def _run_ecological_cca(Y_df: pd.DataFrame, X_df: pd.DataFrame):
    """Run ecological CCA via skbio.stats.ordination.cca.

    Returns the OrdinationResults object.  Raises ImportError if skbio
    is not available (it is already required by module 04 for PERMANOVA).
    """
    try:
        from skbio.stats.ordination import cca as _skbio_cca
    except ImportError as exc:
        raise ImportError(
            "skbio is required for ecological CCA (module 05). "
            "Install with: pip install scikit-bio"
        ) from exc
    return _skbio_cca(Y_df, X_df)


def _permutation_test_cca(Y_df: pd.DataFrame, X_df: pd.DataFrame,
                           obs_eigvals: "pd.Series",
                           n_perms: int, seed: int) -> list[dict]:
    """Axis-wise permutation test for ecological CCA.

    Permutes rows of Y (species matrix) while holding X (environment) fixed.
    Tests H₀: no relationship between species composition and environment.
    p-value = (n null eigenvalues ≥ observed + 1) / (n_perms + 1).

    Only tests the first two axes to keep runtime tractable.
    """
    from skbio.stats.ordination import cca as _skbio_cca

    rng = np.random.default_rng(seed)
    n_test = min(2, len(obs_eigvals))
    null_store = [[] for _ in range(n_test)]

    for _ in range(n_perms):
        idx = rng.permutation(len(Y_df))
        Y_perm = Y_df.iloc[idx].copy()
        Y_perm.index = Y_df.index
        try:
            res_p = _skbio_cca(Y_perm, X_df)
            for k in range(n_test):
                if k < len(res_p.eigvals):
                    null_store[k].append(float(res_p.eigvals.iloc[k]))
        except Exception:
            pass   # skip failed permutations (rare; e.g., singular matrices)

    rows = []
    for k in range(n_test):
        obs_val = float(obs_eigvals.iloc[k])
        null_arr = np.array(null_store[k])
        if len(null_arr) == 0:
            p = float("nan")
        else:
            p = float((np.sum(null_arr >= obs_val) + 1) / (len(null_arr) + 1))
        rows.append({
            "axis": f"CCA{k+1}",
            "eigenvalue": round(obs_val, 6),
            "n_permutations": len(null_arr),
            "p_value": round(p, 4) if np.isfinite(p) else float("nan"),
            "significant_p005": (p <= 0.05) if np.isfinite(p) else False,
        })
    return rows


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root   = ensure_dirs("05_cca_ordination", config)
    out_plots  = out_root / "plots"
    out_tables = out_root / "tables"
    out_models = out_root / "models"

    check_file(config["paths"]["canonical"]["sp_mat_rds"], "sp_mat", required=True)
    check_file(config["paths"]["canonical"]["env_master_csv"], "env_master", required=True)

    sp_mat = load_pickle(config["paths"]["canonical"]["sp_mat_rds"])
    env    = pd.read_csv(config["paths"]["canonical"]["env_master_csv"])

    if isinstance(sp_mat, pd.DataFrame):
        plot_ids     = sp_mat.index.astype(str)
        species_names = sp_mat.columns.astype(str).tolist()
        X_species    = sp_mat.to_numpy(dtype=float)
    else:
        X_species     = np.asarray(sp_mat, dtype=float)
        plot_ids      = pd.Index([f"plot_{i+1}" for i in range(X_species.shape[0])])
        species_names = [f"sp_{i+1}" for i in range(X_species.shape[1])]

    env = env.set_index("plot_id", drop=False).reindex(plot_ids).reset_index(drop=True)

    warnings_list: list[str] = []
    missing_env = int(env["plot_id"].isna().sum()) if "plot_id" in env.columns else 0
    if missing_env > 0:
        warnings_list.append(
            f"{missing_env} plot(s) from sp_mat have no matching row in env_master; "
            "their environmental variables will be imputed by median."
        )

    # ── Select environmental predictors ──────────────────────────────────────
    # Exclude: identifiers, spatial surrogates, synthetic proxies, non-numeric.
    num_vars = [c for c in env.columns if pd.api.types.is_numeric_dtype(env[c])]
    num_vars = [c for c in num_vars if c not in _EXCLUDE_FROM_ORDINATION]

    usable = []
    for c in num_vars:
        s = pd.to_numeric(env[c], errors="coerce")
        if s.isna().mean() < 0.5 and s.std(skipna=True) > 0:
            usable.append(c)

    if not usable:
        raise RuntimeError("No usable numeric environmental predictors for CCA.")

    X_env = env[usable].apply(pd.to_numeric, errors="coerce")
    X_env = X_env.fillna(X_env.median(numeric_only=True))

    # ── Limit species to top-200 most frequent ────────────────────────────────
    MAX_SPECIES = 200
    occ_counts = (X_species > 0).sum(axis=0)
    if X_species.shape[1] > MAX_SPECIES:
        top_idx    = np.argsort(occ_counts)[::-1][:MAX_SPECIES]
        X_species  = X_species[:, top_idx]
        species_names = [species_names[i] for i in top_idx]

    # ── Build DataFrames for skbio CCA ────────────────────────────────────────
    # skbio CCA requires: (a) non-negative species matrix, (b) no all-zero rows
    Y_df = pd.DataFrame(X_species, index=plot_ids, columns=species_names)
    # Drop species with no occurrences (all-zero columns)
    Y_df = Y_df.loc[:, (Y_df > 0).any(axis=0)]
    # Drop plots with zero total abundance (skbio cannot chi-square weight them)
    valid_rows = Y_df.sum(axis=1) > 0
    n_dropped  = int((~valid_rows).sum())
    if n_dropped > 0:
        warnings_list.append(
            f"{n_dropped} plot(s) with zero species abundance dropped before CCA."
        )
    Y_df   = Y_df[valid_rows]
    X_env_df = X_env[valid_rows.values].copy()
    X_env_df.index = Y_df.index

    if len(Y_df) < 10 or Y_df.shape[1] < 2 or X_env_df.shape[1] < 2:
        raise RuntimeError(
            f"Insufficient data after filtering: {len(Y_df)} plots, "
            f"{Y_df.shape[1]} species, {X_env_df.shape[1]} env vars."
        )

    # ── Ecological CCA (ter Braak 1986 via skbio) ─────────────────────────────
    cca_result = _run_ecological_cca(Y_df, X_env_df)

    eigvals   = cca_result.eigvals               # pd.Series  (attr name in skbio)
    prop_exp  = cca_result.proportion_explained  # pd.Series
    n_axes    = len(eigvals)
    n_comp    = min(2, n_axes)

    # ── Axis permutation test ─────────────────────────────────────────────────
    n_perms = min(99, int(config["params"].get("permutations", 99)))
    perm_rows = _permutation_test_cca(
        Y_df, X_env_df, eigvals,
        n_perms=n_perms, seed=config["params"]["seed"]
    )

    # ── Build score tables ────────────────────────────────────────────────────
    # skbio samples: rows = plots, cols = CCA1, CCA2, ...  (index = plot_ids)
    site_arr    = cca_result.samples.iloc[:, :n_comp].values
    site_scores = pd.DataFrame({"plot_id": Y_df.index.tolist()})
    for k in range(n_comp):
        site_scores[f"CCA{k+1}"] = site_arr[:, k]

    # skbio features: rows = species, cols = CCA1, CCA2, ... (index = species names)
    sp_names_used = Y_df.columns.tolist()
    if cca_result.features is not None:
        sp_arr    = cca_result.features.iloc[:, :n_comp].values
        sp_scores = pd.DataFrame({"species_name": cca_result.features.index.tolist()})
        for k in range(n_comp):
            sp_scores[f"CCA{k+1}"] = sp_arr[:, k]
    else:
        sp_scores = pd.DataFrame({"species_name": sp_names_used})

    # skbio biplot_scores: rows = env vars (index = var names), cols = CCA1..k
    if cca_result.biplot_scores is not None:
        bp       = cca_result.biplot_scores.iloc[:, :n_comp]
        env_scores = pd.DataFrame({"variable": bp.index.tolist()})
        for k in range(n_comp):
            env_scores[f"CCA{k+1}"] = bp.iloc[:, k].values
    else:
        env_scores = pd.DataFrame({"variable": usable})

    var_rows = []
    for k in range(n_comp):
        var_rows.append({
            "axis": f"CCA{k+1}",
            "eigenvalue":           round(float(eigvals.iloc[k]), 6),
            "proportion_explained": round(float(prop_exp.iloc[k]), 6),
            "pct_explained":        round(float(prop_exp.iloc[k]) * 100, 2),
        })
    var_df = pd.DataFrame(var_rows)

    perm_df = pd.DataFrame(perm_rows)

    # ── Variance partitioning ─────────────────────────────────────────────────
    climate_kws = {"bio", "mat", "map", "prec", "temp", "arid"}
    topo_kws    = {"elevation", "slope", "aspect", "dem", "altitude"}
    soil_kws    = {"soil", "fao", "clay", "sand", "ph", "bulk"}

    def _classify(col: str) -> str:
        c = col.lower()
        if any(k in c for k in climate_kws):   return "climate"
        if any(k in c for k in topo_kws):      return "topography"
        if any(k in c for k in soil_kws):      return "soil"
        return "other"

    group_cols: dict[str, list[str]] = {}
    for col in usable:
        group_cols.setdefault(_classify(col), []).append(col)

    Y_np    = Y_df.to_numpy(dtype=float)
    X_np    = X_env_df.to_numpy(dtype=float)
    r2_full = _mean_r2(Y_np, X_np)

    vpart_rows = []
    for grp_name, cols in group_cols.items():
        cols_in_env = [c for c in cols if c in X_env_df.columns]
        if not cols_in_env:
            continue
        r2_grp   = _mean_r2(Y_np, X_env_df[cols_in_env].to_numpy())
        other    = [c for c in usable if c not in cols_in_env]
        r2_others = _mean_r2(Y_np, X_env_df[other].to_numpy()) if other else 0.0
        r2_pure  = r2_full - r2_others
        vpart_rows.append({
            "group":                 grp_name,
            "variables":             ", ".join(cols_in_env),
            "n_variables":           len(cols_in_env),
            "adj_r2_group_alone":    round(r2_grp,  4),
            "adj_r2_pure_fraction":  round(r2_pure, 4),
            "adj_r2_full_model":     round(r2_full, 4),
        })
    vpart_rows.append({
        "group":                "FULL MODEL",
        "variables":            ", ".join(usable),
        "n_variables":          len(usable),
        "adj_r2_group_alone":   round(r2_full, 4),
        "adj_r2_pure_fraction": round(r2_full, 4),
        "adj_r2_full_model":    round(r2_full, 4),
    })
    vpart_df = pd.DataFrame(vpart_rows)

    # ── Write outputs ─────────────────────────────────────────────────────────
    f_model   = out_models / "cca_model.rds"
    f_anova   = out_tables / "cca_anova.txt"
    f_site    = out_tables / "cca_site_scores.csv"
    f_species = out_tables / "cca_species_scores.csv"
    f_env_out = out_tables / "cca_env_biplot_scores.csv"
    f_var     = out_tables / "cca_variance_explained.csv"
    f_perm    = out_tables / "cca_permutation_test.csv"
    f_vpart   = out_tables / "variance_partitioning.csv"

    save_pickle(f_model, cca_result)
    site_scores.to_csv(f_site, index=False)
    sp_scores.to_csv(f_species, index=False)
    env_scores.to_csv(f_env_out, index=False)
    var_df.to_csv(f_var, index=False)
    perm_df.to_csv(f_perm, index=False)
    vpart_df.to_csv(f_vpart, index=False)

    anova_lines = [
        "Ecological CCA — Axis Permutation Test",
        "=" * 45,
        f"Method : skbio.stats.ordination.cca (ter Braak 1986)",
        f"Plots  : {len(Y_df)}  |  Species : {Y_df.shape[1]}  |  Env vars : {len(usable)}",
        f"Permutations per axis: {n_perms}",
        "",
        "Axis     Eigenvalue   % Explained   p-value   Significant?",
        "-" * 58,
    ]
    for vr, pr in zip(var_rows, perm_rows):
        sig = "YES" if pr.get("significant_p005") else "no"
        anova_lines.append(
            f"{vr['axis']}   {vr['eigenvalue']:>10.4f}   "
            f"{vr['pct_explained']:>9.2f}%   "
            f"{pr.get('p_value', float('nan')):>7.4f}   {sig}"
        )
    anova_lines += [
        "",
        "Variance partitioning (adj-R², Borcard et al. 1992):",
        f"  Full model : {r2_full:.4f}",
    ]
    for vp in vpart_rows[:-1]:
        anova_lines.append(
            f"  {vp['group']:<14} alone={vp['adj_r2_group_alone']:.4f}  "
            f"pure={vp['adj_r2_pure_fraction']:.4f}"
        )
    f_anova.write_text("\n".join(anova_lines) + "\n", encoding="utf-8")

    # ── Plot: triplot ─────────────────────────────────────────────────────────
    if n_comp >= 2 and "CCA2" in site_scores.columns:
        s1 = site_scores["CCA1"].to_numpy(dtype=float)
        s2 = site_scores["CCA2"].to_numpy(dtype=float)
        s1_scale = max(np.abs(s1).max(), 1e-12)
        s2_scale = max(np.abs(s2).max(), 1e-12)
        s1_n = s1 / s1_scale
        s2_n = s2 / s2_scale

        env_s1 = env_s2 = None
        if "CCA1" in env_scores.columns and "CCA2" in env_scores.columns:
            raw_e1 = env_scores["CCA1"].to_numpy(dtype=float)
            raw_e2 = env_scores["CCA2"].to_numpy(dtype=float)
            e_scale = max(np.sqrt(raw_e1 ** 2 + raw_e2 ** 2).max(), 1e-12)
            env_s1  = raw_e1 / e_scale * 0.85
            env_s2  = raw_e2 / e_scale * 0.85

        # Forest type colours from env (original, unfiltered)
        ft_col = None
        env_full = pd.read_csv(config["paths"]["canonical"]["env_master_csv"])
        env_full = env_full.set_index("plot_id").reindex(Y_df.index)
        for col in ("forest_type", "ForTyp"):
            if col in env_full.columns:
                ft_col = env_full[col].astype(str).tolist()
                break

        pct1 = var_rows[0]["pct_explained"]
        pct2 = var_rows[1]["pct_explained"] if len(var_rows) > 1 else 0.0
        p1   = perm_rows[0]["p_value"]   if perm_rows else float("nan")
        p2   = perm_rows[1]["p_value"]   if len(perm_rows) > 1 else float("nan")

        xlabel_str = (f"CCA1 ({pct1:.1f}% explained, "
                      f"p = {p1:.3f})" if np.isfinite(p1)
                      else f"CCA1 ({pct1:.1f}% explained)")
        ylabel_str = (f"CCA2 ({pct2:.1f}% explained, "
                      f"p = {p2:.3f})" if np.isfinite(p2)
                      else f"CCA2 ({pct2:.1f}% explained)")

        with pub_style():
            fig, ax = plt.subplots(figsize=(7, 6))

            if ft_col is not None:
                unique_fts = sorted(set(ft_col))
                cmap = {ft: FOREST_PALETTE[i % len(FOREST_PALETTE)]
                        for i, ft in enumerate(unique_fts)}
                for ft in unique_fts:
                    idx = [i for i, v in enumerate(ft_col) if v == ft]
                    ax.scatter(s1_n[idx], s2_n[idx], color=cmap[ft],
                               s=16, alpha=0.55, linewidths=0, label=ft,
                               rasterized=True)
                ax.legend(title="Forest type", bbox_to_anchor=(1.01, 1),
                          loc="upper left", framealpha=0.9, edgecolor="0.8",
                          ncol=1, fontsize=8)
            else:
                ax.scatter(s1_n, s2_n, color=FOREST_PALETTE[0],
                           s=16, alpha=0.55, linewidths=0, rasterized=True)

            if env_s1 is not None:
                arrow_scale = 0.85
                for i, var in enumerate(env_scores["variable"]):
                    ax.annotate(
                        "", xy=(env_s1[i] * arrow_scale, env_s2[i] * arrow_scale),
                        xytext=(0, 0),
                        arrowprops=dict(arrowstyle="-|>", color="#E15759", lw=1.2),
                    )
                    ax.text(env_s1[i] * (arrow_scale + 0.08),
                            env_s2[i] * (arrow_scale + 0.08),
                            var, color="#E15759", fontsize=8,
                            ha="center", va="center",
                            bbox=dict(fc="white", ec="none", alpha=0.7, pad=1))

            ax.axhline(0, color="0.6", linewidth=0.6, zorder=0)
            ax.axvline(0, color="0.6", linewidth=0.6, zorder=0)
            ax.set_xlabel(xlabel_str)
            ax.set_ylabel(ylabel_str)
            ax.set_title("Ecological CCA Triplot — Site Scores + Env Vectors\n"
                         "(chi-square constrained ordination, ter Braak 1986)")
            ax.set_xlim(-1.15, 1.15)
            ax.set_ylim(-1.15, 1.15)
            fig.subplots_adjust(right=0.72)
            save_plot(fig, out_plots / "cca_sites.png")

    return {
        "status": "success",
        "outputs": [str(f_model), str(f_anova), str(f_site), str(f_species),
                    str(f_env_out), str(f_var), str(f_perm), str(f_vpart)],
        "warnings": warnings_list,
        "runtime_sec": time.time() - t0,
    }
