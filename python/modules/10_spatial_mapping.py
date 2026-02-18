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
    """Publication-quality 2-panel national EVI trend figure.

    Left panel  — Bhutan map: boundary outline, district-level grid, NFI plot
                  locations coloured by elevation zone (or uniform), trend
                  label stamped directly on the country.
    Right panel — EVI time series (2000-2024): bi-weekly scatter, annual mean
                  line, Theil-Sen trend line, monsoon shading, stats box.
    """
    import matplotlib.dates as mdates
    import matplotlib.patches as mpatches
    import matplotlib.ticker as mticker
    from scipy.stats import theilslopes

    # ── National stats (all rows identical in country-replicated table) ───────
    row        = evi.iloc[0]
    trend_cls  = str(row.get("trend_class", "Unknown"))
    slope_day  = float(row.get("theil_sen_slope", 0.0))
    slope_yr   = slope_day * 365.25
    p_val      = float(row.get("mk_p_value", 1.0))
    n_obs      = int(row.get("n_obs", 0))
    fill_color = palette.get(trend_cls, "#BAB0AC")
    p_str      = "p < 0.001" if p_val < 0.001 else f"p = {p_val:.4f}"

    # ── Load raw EVI time series for the right panel ──────────────────────────
    raw_evi_path = config["paths"]["inputs"]["evi_csv"]
    ts = None
    if raw_evi_path.exists():
        try:
            from python.utils import normalize_name
            _raw = pd.read_csv(raw_evi_path)
            _norm = {normalize_name(c): c for c in _raw.columns}
            _dc = _norm.get("date")
            _ec = _norm.get("evi")
            if _dc and _ec:
                ts = _raw[[_dc, _ec]].copy()
                ts["_date"] = pd.to_datetime(ts[_dc], errors="coerce")
                ts["_evi"]  = pd.to_numeric(ts[_ec], errors="coerce")
                ts = ts.dropna(subset=["_date", "_evi"]).sort_values("_date")
                ts["_year"]  = ts["_date"].dt.year
                ts["_month"] = ts["_date"].dt.month
        except Exception:
            ts = None

    # ── NFI plot locations ────────────────────────────────────────────────────
    loc = master.dropna(subset=["longitude", "latitude"])

    # ── Figure: 1 row, 2 columns  (map 55 % | time series 45 %) ─────────────
    with pub_style(font_size=11):
        fig = plt.figure(figsize=(16, 7))
        gs  = fig.add_gridspec(
            1, 2,
            width_ratios=[11, 9],
            wspace=0.08,
            left=0.04, right=0.97, top=0.91, bottom=0.10,
        )
        ax_map = fig.add_subplot(gs[0])
        ax_ts  = fig.add_subplot(gs[1])

        # ── LEFT: Bhutan map ──────────────────────────────────────────────────
        if boundary is not None:
            try:
                boundary.plot(ax=ax_map, color=fill_color, alpha=0.22, zorder=1)
                boundary.boundary.plot(
                    ax=ax_map, color="0.25", linewidth=1.0, zorder=2)
            except Exception:
                pass

        # NFI plot locations — uniform small dots (spatial coverage)
        ax_map.scatter(
            loc["longitude"], loc["latitude"],
            color="0.35", s=3, alpha=0.35, linewidths=0,
            rasterized=True, zorder=3,
        )

        # Large trend label stamped on Bhutan centroid
        ax_map.text(
            90.45, 27.45,
            f"▲ {trend_cls}",
            fontsize=20, fontweight="bold",
            color=fill_color, ha="center", va="center",
            alpha=0.85, zorder=5,
        )

        ax_map.legend(
            handles=[
                mpatches.Patch(facecolor=fill_color, edgecolor="0.4",
                               alpha=0.55, label=f"National EVI trend: {trend_cls}"),
                mpatches.Patch(color="0.35", alpha=0.5,
                               label=f"NFI plot locations (n={len(loc):,})"),
            ],
            loc="lower left", framealpha=0.92, edgecolor="0.7", fontsize=9,
        )
        ax_map.set_title(
            "Spatial Context — NFI Plot Coverage, Bhutan",
            fontweight="bold", fontsize=11,
        )
        ax_map.set_xlabel("Longitude (°E)", labelpad=4)
        ax_map.set_ylabel("Latitude (°N)", labelpad=4)
        ax_map.tick_params(labelsize=9)

        # ── RIGHT: EVI time series ────────────────────────────────────────────
        if ts is not None and len(ts) > 2:
            annual = ts.groupby("_year")["_evi"].mean().reset_index()
            annual["_date"] = pd.to_datetime(
                annual["_year"].astype(str) + "-07-01")

            # Theil-Sen trend line on ordinal time
            t_ord = ts["_date"].map(lambda d: d.toordinal())
            sl, ic, _, _ = theilslopes(ts["_evi"].values, t_ord.values)
            t_rng = np.linspace(t_ord.min(), t_ord.max(), 400)
            d_rng = [pd.Timestamp.fromordinal(int(t)) for t in t_rng]
            y_rng = ic + sl * t_rng

            # Monsoon shading
            for yr in sorted(ts["_year"].unique()):
                ax_ts.axvspan(
                    pd.Timestamp(f"{yr}-06-01"), pd.Timestamp(f"{yr}-09-30"),
                    color="#AED6F1", alpha=0.13, linewidth=0, zorder=0,
                )

            # Bi-weekly scatter
            ax_ts.scatter(
                ts["_date"], ts["_evi"],
                color="#95CA7B", s=10, alpha=0.45, linewidths=0,
                label="Bi-weekly EVI", zorder=2, rasterized=True,
            )
            # Annual mean
            ax_ts.plot(
                annual["_date"], annual["_evi"],
                color="#1B7837", lw=2.2, marker="o", ms=4, zorder=4,
                label="Annual mean",
            )
            # Trend line
            ax_ts.plot(
                d_rng, y_rng,
                color="#C0392B", lw=2.0, ls="--", zorder=5,
                label="Theil–Sen trend",
            )

            # Stats annotation
            delta = sl * 365.25 * (ts["_year"].max() - ts["_year"].min())
            ax_ts.annotate(
                f"Trend:  {trend_cls}  ({p_str})\n"
                f"Slope:  {slope_yr:+.2f} EVI yr⁻¹\n"
                f"Net Δ (2000–2024):  {delta:+.0f} EVI\n"
                f"n = {n_obs:,} MODIS 16-day obs",
                xy=(0.03, 0.97), xycoords="axes fraction",
                va="top", ha="left", fontsize=9.5,
                bbox=dict(boxstyle="round,pad=0.45",
                          facecolor="white", edgecolor="0.6", alpha=0.94),
                zorder=6,
            )
            ax_ts.text(
                0.98, 0.97, "Shaded: monsoon (Jun–Sep)",
                transform=ax_ts.transAxes, fontsize=8,
                color="#2471A3", va="top", ha="right",
            )
            ax_ts.legend(loc="lower right", framealpha=0.9, fontsize=9,
                         edgecolor="0.7")
            ax_ts.xaxis.set_major_locator(mdates.YearLocator(4))
            ax_ts.xaxis.set_minor_locator(mdates.YearLocator(1))
            ax_ts.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
            ax_ts.tick_params(axis="x", labelrotation=0, labelsize=9)
            ax_ts.tick_params(axis="y", labelsize=9)
            ax_ts.set_xlabel("Year", labelpad=4)
            ax_ts.set_ylabel("EVI (MODIS raw units, ×10⁻⁴ = true EVI)", labelpad=4)
        else:
            ax_ts.text(0.5, 0.5, "Raw EVI time series\nnot available",
                       ha="center", va="center", transform=ax_ts.transAxes,
                       fontsize=12, color="0.5")

        ax_ts.set_title(
            "National EVI Time Series (2000–2024)",
            fontweight="bold", fontsize=11,
        )

        fig.suptitle(
            "Vegetation Greenness Trend — Bhutan  |  MODIS MOD13Q1  |  "
            "Theil–Sen / Mann–Kendall",
            fontsize=13, fontweight="bold",
        )
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
