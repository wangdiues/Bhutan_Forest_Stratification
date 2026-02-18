from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from python.utils import check_file, ensure_dirs, pub_style, save_plot


def _plot_evi_national_map(
    master: pd.DataFrame,
    evi: pd.DataFrame,
    boundary,
    palette: dict,
    out_path,
    config: dict,
) -> None:
    """Publication-quality national EVI trend spatial overview.

    Used when EVI data is a country-aggregate (no per-plot variation).
    Shows Bhutan filled with the national trend colour, NFI plot locations
    as grey dots, and a statistics annotation box.
    """
    import matplotlib.patches as mpatches
    import matplotlib.patheffects as pe

    # Pull national-level stats from first row (all rows are identical).
    row = evi.iloc[0]
    trend_cls   = str(row.get("trend_class", "Unknown"))
    slope_day   = float(row.get("theil_sen_slope", 0.0))
    slope_yr    = slope_day * 365.25          # EVI units per calendar year
    p_val       = float(row.get("mk_p_value", 1.0))
    n_obs       = int(row.get("n_obs", 0))
    fill_color  = palette.get(trend_cls, "#BAB0AC")

    p_str = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.4f}"

    ann_text = (
        f"National EVI Trend:  {trend_cls.upper()}\n\n"
        f"Theil–Sen slope:   {slope_yr:+.2f} EVI yr⁻¹\n"
        f"Mann–Kendall:      {p_str}\n"
        f"Period:             2000 – 2024\n"
        f"Observations:       {n_obs:,} (MODIS 16-day composites)\n\n"
        f"Note: country-aggregate EVI — plot-level data unavailable.\n"
        f"NFI plot locations shown for spatial context only."
    )

    with pub_style(font_size=11):
        fig, ax = plt.subplots(figsize=(10, 8))

        # Fill Bhutan polygon with trend colour (semi-transparent).
        if boundary is not None:
            try:
                boundary.plot(
                    ax=ax,
                    color=fill_color, alpha=0.18,
                    zorder=1,
                )
                boundary.boundary.plot(
                    ax=ax,
                    color="0.30", linewidth=0.9,
                    zorder=2,
                )
            except Exception:
                pass

        # NFI plot locations — grey dots for spatial context.
        loc = master.dropna(subset=["longitude", "latitude"])
        ax.scatter(
            loc["longitude"], loc["latitude"],
            color="#7F7F7F", s=6, alpha=0.45, linewidths=0,
            label=f"NFI plots (n={len(loc):,})",
            rasterized=True, zorder=3,
        )

        # Trend colour swatch in legend.
        trend_patch = mpatches.Patch(
            facecolor=fill_color, edgecolor="0.4", linewidth=0.6,
            label=f"National trend: {trend_cls}",
            alpha=0.65,
        )
        ax.legend(
            handles=[trend_patch,
                     mpatches.Patch(color="#7F7F7F", alpha=0.6, label=f"NFI plots (n={len(loc):,})")],
            loc="lower right", framealpha=0.92, edgecolor="0.7", fontsize=9,
        )

        # Statistics annotation box (upper-left).
        ax.annotate(
            ann_text,
            xy=(0.02, 0.98), xycoords="axes fraction",
            va="top", ha="left", fontsize=9,
            family="monospace",
            bbox=dict(
                boxstyle="round,pad=0.55",
                facecolor="white", edgecolor="0.60", alpha=0.95,
            ),
            zorder=6,
        )

        ax.set_title(
            "Vegetation Greenness Trend — Bhutan  (MODIS MOD13Q1 EVI, 2000–2024)",
            fontweight="bold", fontsize=12, pad=10,
        )
        ax.set_xlabel("Longitude (°E)", labelpad=5)
        ax.set_ylabel("Latitude (°N)", labelpad=5)
        ax.tick_params(labelsize=10)
        fig.tight_layout()
        save_plot(fig, out_path)


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

    evi_df = None
    evi_is_national = False
    if evi_path.exists():
        evi_df = pd.read_csv(evi_path)
        if {"plot_id", "trend_class"}.issubset(evi_df.columns):
            master = master.merge(evi_df[["plot_id", "trend_class"]], on="plot_id", how="left")
        # Detect country-replicated data: trend_unit flag OR all plots share one trend class.
        if "trend_unit" in evi_df.columns:
            evi_is_national = evi_df["trend_unit"].str.contains("country", na=False).all()
        elif "trend_class" in evi_df.columns:
            evi_is_national = evi_df["trend_class"].nunique() <= 1

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
        make_map("richness",  "Species Richness across Bhutan",         "map_species_richness.png"),
        make_map("sci_index", "Stratification Complexity Index (SCI)",  "map_sci_index.png"),
        make_map("NMDS1",     "Beta-Diversity Gradient (NMDS1)",        "map_nmds1_scores.png"),
    ]:
        if m is not None:
            outputs.append(m)

    # EVI trend map — national overview when data is country-aggregate, per-plot scatter otherwise.
    evi_out = out_dir / "map_evi_trends.png"
    if evi_df is not None and evi_is_national:
        _plot_evi_national_map(
            master, evi_df, boundary,
            config["colors"]["trend"], evi_out, config,
        )
        outputs.append(str(evi_out))
        warnings.append(
            "EVI spatial map shows national-aggregate trend (no per-plot EVI data); "
            "NFI plot locations included for spatial context."
        )
    else:
        result = make_map(
            "trend_class", "Vegetation Greenness Trend (EVI)",
            "map_evi_trends.png", discrete=True,
        )
        if result is not None:
            outputs.append(result)

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
