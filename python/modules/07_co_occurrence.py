from __future__ import annotations

import time

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

from python.utils import FOREST_PALETTE, check_file, ensure_dirs, load_pickle, pub_style, save_pickle, save_plot


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
    communities = list(nx.algorithms.community.greedy_modularity_communities(g))
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

    f_nodes = out_tables / "network_node_metrics.csv"
    f_edges = out_tables / "network_edges.csv"
    f_graph = out_models / "co_occurrence_graph.rds"

    node_tbl.to_csv(f_nodes, index=False)
    edge_tbl.to_csv(f_edges, index=False)
    save_pickle(f_graph, g)

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
        "outputs": [str(f_nodes), str(f_edges), str(f_graph)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
