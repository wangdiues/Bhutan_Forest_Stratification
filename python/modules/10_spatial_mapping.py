from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from python.utils import check_file, ensure_dirs, pub_style, save_plot


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_dir = ensure_dirs("10_spatial_mapping", config)
    warnings = []

    alpha_path = config["output"]["module_dirs"]["03_alpha_diversity"] / "tables" / "alpha_diversity_summary.csv"
    nmds_path = config["output"]["module_dirs"]["04_beta_diversity"] / "data" / "nmds_scores.csv"
    sci_path = config["output"]["module_dirs"]["09_sci_index"] / "tables" / "stratification_complexity_index.csv"
    evi_path = config["output"]["module_dirs"]["08b_evi_spatial"] / "tables" / "plot_evi_trends.csv"

    check_file(alpha_path, "Alpha diversity summary", required=True)
    alpha = pd.read_csv(alpha_path)

    if not {"plot_id", "longitude", "latitude"}.issubset(alpha.columns):
        raise RuntimeError("Alpha diversity summary must include plot_id, longitude, latitude for spatial mapping.")

    master = alpha[["plot_id", "longitude", "latitude", "richness"]].copy()

    if sci_path.exists():
        sci = pd.read_csv(sci_path)
        if {"plot_id", "sci_index"}.issubset(sci.columns):
            master = master.merge(sci[["plot_id", "sci_index"]], on="plot_id", how="left")

    if nmds_path.exists():
        nmds = pd.read_csv(nmds_path)
        axis = "NMDS1" if "NMDS1" in nmds.columns else "MDS1" if "MDS1" in nmds.columns else None
        if axis and "plot_id" in nmds.columns:
            master = master.merge(nmds[["plot_id", axis]], on="plot_id", how="left")
            if axis != "NMDS1":
                master = master.rename(columns={axis: "NMDS1"})

    if evi_path.exists():
        evi_df = pd.read_csv(evi_path)
        if {"plot_id", "trend_class"}.issubset(evi_df.columns):
            master = master.merge(evi_df[["plot_id", "trend_class"]], on="plot_id", how="left")
    else:
        warnings.append(f"EVI per-plot trends not found at {evi_path}; map_evi_trends will be skipped.")

    outputs = []
    out_gpkg = out_dir / "spatial_master_points.gpkg"
    try:
        import geopandas as gpd

        gdf = gpd.GeoDataFrame(
            master.copy(),
            geometry=gpd.points_from_xy(master["longitude"], master["latitude"]),
            crs=f"EPSG:{config['params']['crs_epsg']}",
        )
        gdf.to_file(out_gpkg, driver="GPKG")
        outputs.append(str(out_gpkg))

        boundary = None
        if config["paths"]["inputs"]["bhutan_boundary"].exists():
            try:
                boundary = gpd.read_file(config["paths"]["inputs"]["bhutan_boundary"]).to_crs(epsg=config["params"]["crs_epsg"])
            except Exception as exc:
                warnings.append(f"Boundary load failed: {type(exc).__name__}: {exc}")
    except Exception as exc:
        warnings.append(f"Spatial GeoPackage write failed: {type(exc).__name__}: {exc}")
        boundary = None

    _CMAP_LOOKUP = {
        "richness": ("YlGn",   "Species richness"),
        "sci_index": ("RdYlGn", "SCI (z-score sum)"),
        "NMDS1":    ("PuOr",   "NMDS1 score"),
    }

    def make_map(var: str, title: str, file_name: str, discrete: bool = False):
        if var not in master.columns:
            return None
        with pub_style():
            fig, ax = plt.subplots(figsize=(8, 6))
            if boundary is not None:
                boundary.boundary.plot(ax=ax, color="0.45", linewidth=0.7, zorder=3)
            if discrete:
                palette = config["colors"]["trend"]
                counts = master[var].value_counts()
                for cls, sub in master.groupby(var, dropna=False):
                    ax.scatter(
                        sub["longitude"], sub["latitude"],
                        color=palette.get(str(cls), "#BAB0AC"),
                        s=8, alpha=0.75, linewidths=0,
                        label=f"{cls} (n={counts.get(cls, 0):,})",
                        rasterized=True,
                    )
                ax.legend(title=var.replace("_", " ").title(),
                          framealpha=0.9, edgecolor="0.8", fontsize=8,
                          loc="lower right")
            else:
                cmap_name, cb_label = _CMAP_LOOKUP.get(var, ("viridis", var))
                sc = ax.scatter(
                    master["longitude"], master["latitude"],
                    c=master[var], cmap=cmap_name,
                    s=9, alpha=0.8, linewidths=0, rasterized=True,
                )
                cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.02)
                cb.set_label(cb_label, fontsize=9)
                cb.ax.tick_params(labelsize=8)
            ax.set_title(title)
            ax.set_xlabel("Longitude (°E)")
            ax.set_ylabel("Latitude (°N)")
            ax.tick_params(labelsize=9)
            fig.tight_layout()
            save_plot(fig, out_dir / file_name)
        return str(out_dir / file_name)

    for m in [
        make_map("richness",    "Species Richness across Bhutan",               "map_species_richness.png"),
        make_map("sci_index",   "Stratification Complexity Index (SCI)",        "map_sci_index.png"),
        make_map("NMDS1",       "Beta-Diversity Gradient (NMDS1)",              "map_nmds1_scores.png"),
        make_map("trend_class", "Vegetation Greenness Trend (EVI, 2000–2024)",  "map_evi_trends.png", discrete=True),
    ]:
        if m is not None:
            outputs.append(m)

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
