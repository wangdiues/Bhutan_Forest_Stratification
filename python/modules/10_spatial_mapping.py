from __future__ import annotations

import time

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

from python.utils import check_file, ensure_dirs, pub_style, save_plot


# Colormap and label config for continuous variables
_CMAP_CFG = {
    "richness":  ("YlGn",   "Species richness (S)", False),
    "sci_index": ("RdYlGn", "SCI (z-score sum)",    True),   # True = centre at 0
    "NMDS1":     ("PuOr",   "NMDS1 score",           True),
}

# EVI discrete plot order (Stable at back, Browning on top so rare dots visible)
_EVI_ORDER = ["Stable", "No data", "Greening", "Browning"]


def _make_spatial_map(
    master: pd.DataFrame,
    var: str,
    title: str,
    file_path,
    boundary,
    config: dict,
    discrete: bool = False,
) -> str | None:
    """Render a publication-quality scatter map of NFI plot locations."""
    if var not in master.columns:
        return None

    with pub_style(font_size=11):
        fig, ax = plt.subplots(figsize=(10, 7))

        # ── Bhutan territory fill + boundary ─────────────────────────────────
        if boundary is not None:
            try:
                boundary.plot(ax=ax, color="#F4F4EF", alpha=0.90, zorder=0)
                boundary.boundary.plot(ax=ax, color="0.25",
                                       linewidth=0.9, zorder=4)
            except Exception:
                pass

        if discrete:
            # ── Discrete: EVI trend classes ───────────────────────────────────
            palette = config["colors"]["trend"]
            valid = master.dropna(subset=[var])
            total = len(valid)

            for cls in _EVI_ORDER:
                sub = valid[valid[var] == cls]
                if sub.empty:
                    continue
                pct = len(sub) / total * 100
                ax.scatter(
                    sub["longitude"], sub["latitude"],
                    color=palette.get(cls, "#AAAAAA"),
                    s=9, alpha=0.78, linewidths=0,
                    label=f"{cls}  (n={len(sub):,},  {pct:.1f}%)",
                    rasterized=True, zorder=3,
                )
            ax.legend(
                title="EVI trend class  (p ≤ 0.05)",
                title_fontsize=9,
                framealpha=0.95, edgecolor="0.6",
                fontsize=9, loc="lower right",
            )

        else:
            # ── Continuous: richness, SCI, NMDS1 ─────────────────────────────
            cmap_name, cb_label, centre = _CMAP_CFG.get(var, ("viridis", var, False))
            valid = master.dropna(subset=[var])
            vals = valid[var]
            vmin, vmax = vals.quantile(0.02), vals.quantile(0.98)
            if centre:                         # diverging: centre at 0
                vabs = max(abs(vmin), abs(vmax))
                vmin, vmax = -vabs, vabs

            sc = ax.scatter(
                valid["longitude"], valid["latitude"],
                c=vals, cmap=cmap_name, vmin=vmin, vmax=vmax,
                s=10, alpha=0.85, linewidths=0,
                rasterized=True, zorder=3,
            )
            cb = fig.colorbar(sc, ax=ax, shrink=0.62, pad=0.03, aspect=22,
                              extend="both")
            cb.set_label(cb_label, fontsize=9.5)
            cb.ax.tick_params(labelsize=8.5)
            if centre:
                cb.ax.axhline(0, color="0.3", lw=0.8)   # zero line on colorbar

        ax.set_title(title, fontweight="bold", fontsize=12, pad=8)
        ax.set_xlabel("Longitude (°E)", labelpad=4)
        ax.set_ylabel("Latitude (°N)", labelpad=4)
        ax.tick_params(labelsize=9.5)

        # Constrain to Bhutan bbox (from config)
        bb = config["params"]["bhutan_bbox"]
        ax.set_xlim(bb["lon_min"] - 0.15, bb["lon_max"] + 0.15)
        ax.set_ylim(bb["lat_min"] - 0.15, bb["lat_max"] + 0.15)

        fig.tight_layout()
        save_plot(fig, file_path)

    return str(file_path)


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_dir = ensure_dirs("10_spatial_mapping", config)
    warnings = []

    # ── Input tables ──────────────────────────────────────────────────────────
    alpha_path = (config["output"]["module_dirs"]["03_alpha_diversity"]
                  / "tables" / "alpha_diversity_summary.csv")
    nmds_path  = (config["output"]["module_dirs"]["04_beta_diversity"]
                  / "data" / "nmds_scores.csv")
    sci_path   = (config["output"]["module_dirs"]["09_sci_index"]
                  / "tables" / "stratification_complexity_index.csv")
    evi_path   = (config["output"]["module_dirs"]["08_evi_spatial"]
                  / "tables" / "plot_evi_trends.csv")

    check_file(alpha_path, "Alpha diversity summary", required=True)
    alpha = pd.read_csv(alpha_path)

    if not {"plot_id", "longitude", "latitude"}.issubset(alpha.columns):
        raise RuntimeError(
            "Alpha diversity summary must include plot_id, longitude, "
            "latitude for spatial mapping.")

    master = alpha[["plot_id", "longitude", "latitude", "richness"]].copy()

    if sci_path.exists():
        sci = pd.read_csv(sci_path)
        if {"plot_id", "sci_index"}.issubset(sci.columns):
            master = master.merge(sci[["plot_id", "sci_index"]],
                                  on="plot_id", how="left")

    if nmds_path.exists():
        nmds = pd.read_csv(nmds_path)
        axis = ("NMDS1" if "NMDS1" in nmds.columns
                else "MDS1" if "MDS1" in nmds.columns else None)
        if axis and "plot_id" in nmds.columns:
            master = master.merge(nmds[["plot_id", axis]], on="plot_id", how="left")
            if axis != "NMDS1":
                master = master.rename(columns={axis: "NMDS1"})

    if evi_path.exists():
        evi_df = pd.read_csv(evi_path)
        if {"plot_id", "trend_class"}.issubset(evi_df.columns):
            master = master.merge(evi_df[["plot_id", "trend_class"]],
                                  on="plot_id", how="left")
    else:
        warnings.append(
            f"EVI per-plot trends not found at {evi_path}; "
            "map_evi_trends will be skipped.")

    # ── GeoPackage ────────────────────────────────────────────────────────────
    outputs = []
    out_gpkg = out_dir / "spatial_master_points.gpkg"
    boundary = None
    try:
        import geopandas as gpd
        gdf = gpd.GeoDataFrame(
            master.copy(),
            geometry=gpd.points_from_xy(master["longitude"], master["latitude"]),
            crs=f"EPSG:{config['params']['crs_epsg']}",
        )
        gdf.to_file(out_gpkg, driver="GPKG")
        outputs.append(str(out_gpkg))

        bnd_path = config["paths"]["inputs"]["bhutan_boundary"]
        if bnd_path.exists():
            try:
                boundary = gpd.read_file(bnd_path).to_crs(
                    epsg=config["params"]["crs_epsg"])
            except Exception as exc:
                warnings.append(f"Boundary load failed: {type(exc).__name__}: {exc}")
    except Exception as exc:
        warnings.append(f"GeoPackage write failed: {type(exc).__name__}: {exc}")

    # ── Publication-quality spatial maps ─────────────────────────────────────
    map_specs = [
        ("richness",    "Species Richness across Bhutan  (NFI plots)",
         "map_species_richness.png", False),
        ("sci_index",   "Stratification Complexity Index (SCI) — NFI plots",
         "map_sci_index.png",       False),
        ("NMDS1",       "Beta-Diversity Gradient (NMDS1) — NFI plots",
         "map_nmds1_scores.png",    False),
        ("trend_class", "Vegetation Greenness Trend  (EVI, 2000–2024) — NFI plots",
         "map_evi_trends.png",      True),
    ]

    for var, title, fname, discrete in map_specs:
        try:
            result = _make_spatial_map(
                master, var, title,
                out_dir / fname,
                boundary, config,
                discrete=discrete,
            )
            if result is not None:
                outputs.append(result)
        except Exception as exc:
            warnings.append(f"{fname} failed: {type(exc).__name__}: {exc}")

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
