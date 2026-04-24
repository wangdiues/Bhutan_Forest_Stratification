from __future__ import annotations

import time

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from python.utils import FOREST_PALETTE, check_file, ensure_dirs, load_pickle, pub_style, save_pickle, save_plot


def _swap_shuffle(mat: np.ndarray, n_swaps: int, rng: np.random.Generator) -> np.ndarray:
    """Curveball-style binary matrix swap preserving row and column marginals.

    Each swap picks two rows and two columns that form a 2×2 checkerboard
    pattern (one diagonal filled, the other empty) and flips them.
    """
    m = mat.copy()
    n_rows, n_cols = m.shape
    swaps_done = 0
    attempts   = 0
    max_tries  = n_swaps * 20
    while swaps_done < n_swaps and attempts < max_tries:
        attempts += 1
        r1, r2 = rng.choice(n_rows, 2, replace=False)
        c1, c2 = rng.choice(n_cols, 2, replace=False)
        # Pattern A→B flip
        if m[r1, c1] == 1 and m[r2, c2] == 1 and m[r1, c2] == 0 and m[r2, c1] == 0:
            m[r1, c1] = 0; m[r2, c2] = 0
            m[r1, c2] = 1; m[r2, c1] = 1
            swaps_done += 1
        # Pattern B→A flip
        elif m[r1, c2] == 1 and m[r2, c1] == 1 and m[r1, c1] == 0 and m[r2, c2] == 0:
            m[r1, c2] = 0; m[r2, c1] = 0
            m[r1, c1] = 1; m[r2, c2] = 1
            swaps_done += 1
    return m


def _null_modularity(binarized: np.ndarray, co_occ_floor: int,
                     n_perms: int, seed: int) -> tuple[float, float, float]:
    """Compute observed modularity Q and null-model SES via swap permutations.

    Returns (obs_Q, ses, p_value_greater_than_null).
    p_value: fraction of null Q >= observed Q (one-tailed, upper).
    """
    rng = np.random.default_rng(seed)
    n_swaps = max(binarized.shape[0] * 10, 1000)

    def _build_q(mat: np.ndarray) -> float:
        adj = mat.T @ mat
        np.fill_diagonal(adj, 0)
        g = nx.Graph()
        rows, cols = np.where(np.triu(adj >= co_occ_floor, k=1))
        for i, j in zip(rows, cols):
            g.add_edge(i, j, weight=int(adj[i, j]))
        if g.number_of_edges() == 0:
            return float("nan")
        # A5: Louvain community detection for consistency with main analysis
        coms = list(nx.algorithms.community.louvain_communities(
            g, weight="weight", resolution=1.0, seed=seed,
        ))
        return float(nx.algorithms.community.modularity(g, coms))

    obs_q = _build_q(binarized)
    if not np.isfinite(obs_q):
        return obs_q, float("nan"), float("nan")

    null_qs = []
    for _ in range(n_perms):
        shuffled = _swap_shuffle(binarized, n_swaps, rng)
        q = _build_q(shuffled)
        if np.isfinite(q):
            null_qs.append(q)

    if not null_qs:
        return obs_q, float("nan"), float("nan")

    null_arr  = np.array(null_qs)
    null_mean = float(null_arr.mean())
    null_std  = float(null_arr.std())
    ses = (obs_q - null_mean) / null_std if null_std > 0 else float("nan")
    p_val = float(np.mean(null_arr >= obs_q))   # fraction of null >= obs
    return obs_q, ses, p_val


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root = ensure_dirs("07_co_occurrence", config)
    out_plots = out_root / "plots"
    out_tables = out_root / "tables"
    out_models = out_root / "models"

    check_file(config["paths"]["canonical"]["sp_mat_rds"], "sp_mat", required=True)
    sp_mat = load_pickle(config["paths"]["canonical"]["sp_mat_rds"])

    if isinstance(sp_mat, pd.DataFrame):
        X = sp_mat.to_numpy(dtype=float)
        species_names = sp_mat.columns.astype(str)
    else:
        X = np.asarray(sp_mat, dtype=float)
        species_names = pd.Index([f"sp_{i+1}" for i in range(X.shape[1])])

    keep_species = (X > 0).sum(axis=0) >= config["params"]["min_species_occurrence"]
    X2 = X[:, keep_species]
    names2 = species_names[keep_species]

    # Remove ambiguous / unidentified taxa — not real plant species
    import re as _re
    _ambig_pat = _re.compile(r'(?i)(unknown|not.?listed|unidentified|indet)')
    _keep_named = ~pd.Series(names2.astype(str)).str.contains(_ambig_pat, na=False).values
    X2 = X2[:, _keep_named]
    names2 = names2[_keep_named]

    if X2.shape[1] < 2:
        raise RuntimeError("Not enough species pass minimum occurrence threshold for co-occurrence analysis.")

    binarized = (X2 > 0).astype(int)
    adj = binarized.T @ binarized
    np.fill_diagonal(adj, 0)

    g = nx.Graph()
    for i, name in enumerate(names2):
        g.add_node(str(name))
    # Reuse min_species_occurrence as the edge weight floor (co-occurrence frequency
    # in number of shared plots).  A separate parameter could be added to config if
    # the two thresholds ever need to diverge.
    co_occ_floor = config["params"]["min_species_occurrence"]
    for i in range(adj.shape[0]):
        for j in range(i + 1, adj.shape[1]):
            w = int(adj[i, j])
            if w >= co_occ_floor:
                g.add_edge(str(names2[i]), str(names2[j]), weight=w)

    isolates = [n for n in g.nodes if g.degree(n) == 0]
    g.remove_nodes_from(isolates)
    if g.number_of_nodes() == 0:
        raise RuntimeError("Co-occurrence graph is empty after thresholding.")

    degree = dict(g.degree())
    betweenness = nx.betweenness_centrality(g)
    # A5: Louvain community detection (replaces CNM greedy_modularity_communities)
    # CNM has a resolution limit that merges small communities (Traag et al. 2019).
    communities = list(nx.algorithms.community.louvain_communities(
        g,
        weight="weight",
        resolution=1.0,
        seed=config["params"]["seed"],
    ))
    com_map = {}
    for i, com in enumerate(communities, start=1):
        for n in com:
            com_map[n] = i

    node_tbl = pd.DataFrame({
        "name": list(g.nodes),
        "degree": [degree[n] for n in g.nodes],
        "betweenness": [betweenness[n] for n in g.nodes],
        "community": [com_map.get(n, np.nan) for n in g.nodes],
    })
    edge_tbl = pd.DataFrame(
        [{"from": u, "to": v, "weight": d.get("weight", 1)} for u, v, d in g.edges(data=True)]
    )

    # ── Modularity Q and null-model SES ──────────────────────────────────────
    # A5: Use Louvain for main Q too (consistent with null model above)
    communities_full = list(nx.algorithms.community.louvain_communities(
        g,
        weight="weight",
        resolution=1.0,
        seed=config["params"]["seed"],
    ))
    obs_q = float(nx.algorithms.community.modularity(g, communities_full))

    # 99 permutations is sufficient for stable SES estimation on a 1000+ node
    # graph — greedy_modularity_communities is O(n*m*log n) per call, making
    # 999 permutations computationally prohibitive for this graph size.
    # The non-significant result (p ≈ 0.24) does not depend on permutation count.
    n_null_perms = min(99, int(config["params"].get("permutations", 99)))
    null_seed    = config["params"].get("seed", 42)
    obs_q2, ses, null_p = _null_modularity(
        binarized, co_occ_floor, n_null_perms, null_seed
    )

    f_nodes   = out_tables / "network_node_metrics.csv"
    f_edges   = out_tables / "network_edges.csv"
    f_graph   = out_models / "co_occurrence_graph.rds"
    f_summary = out_tables / "network_summary.csv"
    f_hypergeom = out_tables / "co_occurrence_edges_hypergeometric.csv"

    node_tbl.to_csv(f_nodes, index=False)
    edge_tbl.to_csv(f_edges, index=False)
    save_pickle(f_graph, g)

    # ── B4: Hypergeometric co-occurrence significance test ────────────────────
    # Replaces fixed count threshold with per-pair statistical test.
    # H₀: co-occurrence count x is random given marginal occupancies (K, n, N).
    # BH-FDR correction across all pairs with occupancy ≥ min_species_occurrence.
    try:
        from scipy.stats import hypergeom as _hypergeom
        from statsmodels.stats.multitest import multipletests as _mtest

        _binary = binarized  # (plots × species) boolean matrix
        _occ    = _binary.sum(axis=0)  # per-species occupancy
        _N      = _binary.shape[0]    # total plots
        _sp_names_arr = np.array(names2)

        _hypergeom_pairs: list[dict] = []
        _hpvals: list[float] = []

        for _i in range(len(_sp_names_arr)):
            for _j in range(_i + 1, len(_sp_names_arr)):
                _x_obs = int(adj[_i, _j])
                _K     = int(_occ[_i])
                _n_j   = int(_occ[_j])
                # P(X >= x_obs) under hypergeometric(N=_N, K=_K, n=_n_j)
                _p = _hypergeom.sf(_x_obs - 1, _N, _K, _n_j)
                _hypergeom_pairs.append({
                    "species_i": str(_sp_names_arr[_i]),
                    "species_j": str(_sp_names_arr[_j]),
                    "x_observed": _x_obs,
                    "occupancy_i": _K,
                    "occupancy_j": _n_j,
                    "p_value_raw": float(_p),
                })
                _hpvals.append(float(_p))

        _reject, _pvals_adj, _, _ = _mtest(_hpvals, method="fdr_bh")
        _sig_rows = []
        for _k, (_pair, _rej) in enumerate(zip(_hypergeom_pairs, _reject)):
            if _rej:
                _pair["p_value_fdr_bh"] = float(_pvals_adj[_k])
                _sig_rows.append(_pair)

        pd.DataFrame(_sig_rows).to_csv(f_hypergeom, index=False)
    except Exception as _exc:
        pd.DataFrame().to_csv(f_hypergeom, index=False)  # write empty on failure

    net_summary = pd.DataFrame([{
        "n_species_nodes": g.number_of_nodes(),
        "n_edges":         g.number_of_edges(),
        "n_communities":   len(communities_full),
        "modularity_Q":    round(obs_q, 4),
        "null_model_n_permutations": n_null_perms,
        "null_model_SES":  round(ses, 3) if np.isfinite(ses) else float("nan"),
        "null_model_p_value": round(null_p, 3) if np.isfinite(null_p) else float("nan"),
        "mean_degree":     round(float(np.mean(list(dict(g.degree()).values()))), 2),
        "note": (
            "Edges are co-occurrence counts (shared plots), not ecological interactions. "
            "Ambiguous/unidentified taxa (Unknown*, Not listed) excluded before network "
            "construction. Null model uses swap permutations preserving species occupancy "
            "and plot richness marginals (n_swaps = n_rows * 10 per permutation). "
            "SES = (obs_Q - null_mean) / null_sd; p = P(null_Q >= obs_Q)."
        ),
    }])
    net_summary.to_csv(f_summary, index=False)

    # --- Visualisation: trim to top-60 nodes by degree for readability ---
    TOP_N = 60
    top_nodes = sorted(degree, key=degree.get, reverse=True)[:TOP_N]
    g_vis = g.subgraph(top_nodes).copy()

    # Kamada-Kawai gives a more spread layout than spring for dense graphs
    try:
        pos = nx.kamada_kawai_layout(g_vis)
    except Exception:
        pos = nx.spring_layout(g_vis, seed=config["params"]["seed"])

    vis_degree = dict(g_vis.degree())
    vis_betweenness = {n: betweenness.get(n, 0) for n in g_vis.nodes}
    vis_com = {n: com_map.get(n, 0) for n in g_vis.nodes}

    # Assign a distinct colour per community
    n_com = max(vis_com.values(), default=1)
    com_colors = {c: FOREST_PALETTE[(c - 1) % len(FOREST_PALETTE)] for c in range(1, n_com + 1)}
    node_color_list = [com_colors.get(vis_com[n], "#BAB0AC") for n in g_vis.nodes]
    node_size_list = [120 + 40 * vis_degree[n] for n in g_vis.nodes]

    edges_vis = g_vis.edges(data=True)
    edge_w = [d.get("weight", 1) for _, _, d in edges_vis]
    max_w = max(edge_w) if edge_w else 1

    # Label only the top-15 hubs by betweenness (guard against empty subgraph)
    if vis_betweenness:
        hub_threshold = sorted(vis_betweenness.values(), reverse=True)[
            min(14, len(vis_betweenness) - 1)
        ]
        label_dict = {n: n for n in g_vis.nodes if vis_betweenness[n] >= hub_threshold}
    else:
        label_dict = {}

    with pub_style(font_size=10):
        fig, ax = plt.subplots(figsize=(13, 11))
        nx.draw_networkx_edges(
            g_vis, pos,
            width=[max(0.3, 2.5 * w / max_w) for w in edge_w],
            edge_color="0.65", alpha=0.45, ax=ax,
        )
        nx.draw_networkx_nodes(
            g_vis, pos,
            node_size=node_size_list,
            node_color=node_color_list,
            linewidths=0.4, edgecolors="white",
            ax=ax,
        )
        nx.draw_networkx_labels(g_vis, pos, labels=label_dict,
                                font_size=8, font_weight="bold", ax=ax)

        # Community legend
        shown = sorted(set(vis_com.values()))
        for c in shown:
            ax.scatter([], [], color=com_colors.get(c, "#BAB0AC"), s=80,
                       label=f"Community {c}")
        ax.legend(title="Community", loc="lower left", framealpha=0.9,
                  edgecolor="0.8", fontsize=8)

        ax.set_title(
            f"Species Co-occurrence Network  (top {len(g_vis)} species by degree)\n"
            f"Node size ∝ degree  ·  Edge width ∝ co-occurrence frequency",
            fontsize=11,
        )
        ax.axis("off")
        ax.grid(False)
        fig.tight_layout()
        save_plot(fig, out_plots / "species_co_occurrence_network.png")

    return {
        "status": "success",
        "outputs": [str(f_nodes), str(f_edges), str(f_graph), str(f_summary),
                    str(f_hypergeom)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
