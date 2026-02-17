from __future__ import annotations

import time

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

try:
    from utils import check_file, ensure_dirs, load_pickle, save_pickle, save_plot
except ImportError:
    from python.utils import check_file, ensure_dirs, load_pickle, save_pickle, save_plot


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
    for i in range(adj.shape[0]):
        for j in range(i + 1, adj.shape[1]):
            w = int(adj[i, j])
            if w >= config["params"]["min_species_occurrence"]:
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

    pos = nx.spring_layout(g, seed=config["params"]["seed"])
    fig, ax = plt.subplots(figsize=(12, 10))
    edges = g.edges(data=True)
    edge_w = [d.get("weight", 1) for _, _, d in edges]
    nx.draw_networkx_edges(g, pos, width=[max(0.3, w / max(edge_w)) for w in edge_w], alpha=0.4, ax=ax)
    node_colors = [com_map.get(n, 0) for n in g.nodes]
    node_sizes = [80 + 30 * degree[n] for n in g.nodes]
    nx.draw_networkx_nodes(g, pos, node_size=node_sizes, node_color=node_colors, cmap="viridis", ax=ax)
    nx.draw_networkx_labels(g, pos, font_size=7, ax=ax)
    ax.set_title("Species co-occurrence network")
    ax.axis("off")
    save_plot(fig, out_plots / "species_co_occurrence_network.png")

    return {
        "status": "success",
        "outputs": [str(f_nodes), str(f_edges), str(f_graph)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
