from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from utils import check_file, ensure_dirs, save_plot
except ImportError:
    from python.utils import check_file, ensure_dirs, save_plot


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_dir = ensure_dirs("10_spatial_mapping", config)
    warnings = []

    alpha_path = config["output"]["module_dirs"]["03_alpha_diversity"] / "tables" / "alpha_diversity_summary.csv"
    nmds_path = config["output"]["module_dirs"]["04_beta_diversity"] / "data" / "nmds_scores.csv"
    sci_path = config["output"]["module_dirs"]["09_sci_index"] / "tables" / "stratification_complexity_index.csv"
    evi_path = config["output"]["module_dirs"]["08_evi_trends"] / "tables" / "evi_trend_analysis.csv"

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
        evi = pd.read_csv(evi_path)
        if {"plot_id", "trend_class"}.issubset(evi.columns):
            master = master.merge(evi[["plot_id", "trend_class"]], on="plot_id", how="left")

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

    def make_map(var: str, title: str, file_name: str, discrete: bool = False):
        if var not in master.columns:
            return None
        fig, ax = plt.subplots(figsize=(8, 6))
        if boundary is not None:
            boundary.boundary.plot(ax=ax, color="grey", linewidth=0.5)
        if discrete:
            palette = config["colors"]["trend"]
            for cls, sub in master.groupby(var, dropna=False):
                ax.scatter(sub["longitude"], sub["latitude"], alpha=0.85, color=palette.get(str(cls), "grey"), label=str(cls))
            ax.legend(title=var)
        else:
            sc = ax.scatter(master["longitude"], master["latitude"], c=master[var], alpha=0.85, cmap="viridis")
            fig.colorbar(sc, ax=ax, label=var)
        ax.set_title(title)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        save_plot(fig, out_dir / file_name)
        return str(out_dir / file_name)

    for m in [
        make_map("richness", "Species Richness", "map_species_richness.png"),
        make_map("sci_index", "SCI", "map_sci_index.png"),
        make_map("NMDS1", "NMDS1", "map_nmds1_scores.png"),
        make_map("trend_class", "EVI Trend", "map_evi_trends.png", discrete=True),
    ]:
        if m is not None:
            outputs.append(m)

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
