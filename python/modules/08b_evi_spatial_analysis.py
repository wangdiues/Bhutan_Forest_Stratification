"""08b_evi_spatial_analysis — Per-plot EVI trend extraction and integrated analysis.

Inputs (GeoTIFF rasters from GEE, 250 m, EPSG:4326):
  • Bhutan_EVI_TheilSenSlope_2000_2024.tif          (1 band: sen_slope EVI/yr)
  • Bhutan_EVI_MannKendall_tau_p_2000_2024.tif      (2 bands: tau, p-value)
  • Bhutan_MOD13Q1_EVI_AnnualMean_2000_2024_STACK_QA.tif  (25 bands: 2000-2024)

Inputs (pipeline outputs):
  • outputs/alpha_diversity/tables/alpha_diversity_summary.csv
  • outputs/sci_index/tables/stratification_complexity_index.csv

Outputs:
  tables/
    plot_evi_trends.csv          — per-plot slope, tau, p, mean EVI, trend class
    evi_by_elevation_band.csv    — 500-m band summaries
    evi_by_forest_type.csv       — forest type summaries
    evi_area_stats.csv           — pixel-level % greening/browning/stable
  plots/
    evi_slope_vs_elevation.png   — scatter + rolling mean, coloured by trend class
    evi_slope_by_forest_type.png — horizontal box plots sorted by median slope
    evi_slope_vs_richness_sci.png— 2-panel: slope ~ richness and slope ~ SCI
    evi_spatial_trend_map.png    — raster map of significant greening/browning
    evi_integrated_panel.png     — 4-panel publication figure
"""
from __future__ import annotations

import time
import warnings as _warnings

import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

from python.utils import check_file, ensure_dirs, pub_style, save_plot


# ── helpers ───────────────────────────────────────────────────────────────────

def _sample_raster(path, coords: list[tuple[float, float]], band: int = 1) -> np.ndarray:
    """Sample a single raster band at (lon, lat) coordinate pairs."""
    import rasterio
    with rasterio.open(path) as src:
        raw = np.array([list(src.sample([c]))[0] for c in coords], dtype=float)
    vals = raw[:, band - 1]
    vals[~np.isfinite(vals)] = np.nan
    return vals


def _sample_stack_mean(path, coords: list[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample all bands of an annual EVI stack; return (mean, band1, last_band)."""
    import rasterio
    with rasterio.open(path) as src:
        n_bands = src.count
        raw = np.array([list(src.sample([c]))[0] for c in coords], dtype=float)
    raw[~np.isfinite(raw)] = np.nan
    mean_evi = np.nanmean(raw, axis=1)
    return mean_evi, raw[:, 0], raw[:, n_bands - 1]


def _mk_tau_to_pvalue(tau: np.ndarray, n: int = 25) -> np.ndarray:
    """Compute two-tailed Mann-Kendall p-value from tau using normal approximation.

    For n=25 annual observations (no ties assumed):
      Var(S) = n(n-1)(2n+5) / 18
      S      = tau * n(n-1) / 2
      Z      = (S ∓ 1) / sqrt(Var(S))   (continuity correction)
      p      = 2 * (1 - Phi(|Z|))
    """
    var_s = n * (n - 1) * (2 * n + 5) / 18.0
    s_stat = tau * n * (n - 1) / 2.0
    # continuity correction
    z = np.where(s_stat > 0, (s_stat - 1) / np.sqrt(var_s),
        np.where(s_stat < 0, (s_stat + 1) / np.sqrt(var_s), 0.0))
    p = 2.0 * (1.0 - stats.norm.cdf(np.abs(z)))
    p[~np.isfinite(tau)] = np.nan
    return p


def _classify_pixel(slope: float, pval: float, sig: float = 0.05) -> str:
    if np.isnan(slope) or np.isnan(pval):
        return "No data"
    if pval <= sig and slope > 0:
        return "Greening"
    if pval <= sig and slope < 0:
        return "Browning"
    return "Stable"


_ELEV_BINS   = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 6000]
_ELEV_LABELS = ["<500 m", "500–1k m", "1k–1.5k m", "1.5k–2k m",
                "2k–2.5k m", "2.5k–3k m", "3k–3.5k m", "3.5k–4k m", ">4k m"]

_TREND_PALETTE = {"Greening": "#1B7837", "Browning": "#8C510A",
                  "Stable": "#878787", "No data": "#D3D3D3"}


# ── plot helpers ──────────────────────────────────────────────────────────────

def _plot_slope_vs_elevation(df: pd.DataFrame, out_path) -> None:
    """Scatter of Theil-Sen slope vs elevation with rolling mean + zero line."""
    sub = df.dropna(subset=["sen_slope", "elevation"]).copy()
    sub = sub.sort_values("elevation")
    # rolling mean (window = 120 plots ≈ smooth curve)
    sub["roll_mean"] = sub["sen_slope"].rolling(window=120, center=True, min_periods=30).mean()

    with pub_style(font_size=11):
        fig, ax = plt.subplots(figsize=(10, 6))

        # Scatter coloured by trend class
        for cls, grp in sub.groupby("trend_class"):
            ax.scatter(grp["elevation"], grp["sen_slope"],
                       color=_TREND_PALETTE.get(cls, "#999"),
                       s=8, alpha=0.40, linewidths=0,
                       label=f"{cls} (n={len(grp):,})", rasterized=True, zorder=2)

        # Rolling mean
        ax.plot(sub["elevation"], sub["roll_mean"],
                color="black", lw=2.2, zorder=5, label="Rolling mean (n=120)")

        # Zero line
        ax.axhline(0, color="0.4", lw=1.0, ls="--", zorder=3)

        # Correlation annotation
        r, p = stats.pearsonr(sub["elevation"], sub["sen_slope"])
        p_str = "p < 0.001" if p < 0.001 else f"p = {p:.3f}"
        ax.annotate(f"r = {r:.3f},  {p_str}  (n = {len(sub):,})",
                    xy=(0.02, 0.97), xycoords="axes fraction",
                    va="top", fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                              edgecolor="0.6", alpha=0.92))

        ax.set_title("EVI Trend (Theil–Sen Slope) vs Elevation — NFI Plots",
                     fontweight="bold")
        ax.set_xlabel("Elevation (m a.s.l.)", labelpad=4)
        ax.set_ylabel("EVI trend slope (EVI yr⁻¹)", labelpad=4)
        ax.legend(loc="upper right", framealpha=0.9, fontsize=9, edgecolor="0.7")
        fig.tight_layout()
        save_plot(fig, out_path)


def _plot_slope_by_forest_type(df: pd.DataFrame, out_path) -> None:
    """Horizontal box plots of slope by forest type, sorted by median."""
    sub = df.dropna(subset=["sen_slope", "forest_type"])
    order = (sub.groupby("forest_type")["sen_slope"]
               .median().sort_values().index.tolist())
    data_by_type = [sub.loc[sub["forest_type"] == ft, "sen_slope"].values
                    for ft in order]
    medians = [np.median(d) for d in data_by_type]
    colors = [_TREND_PALETTE["Greening"] if m > 0 else _TREND_PALETTE["Browning"]
              for m in medians]

    with pub_style(font_size=11):
        fig, ax = plt.subplots(figsize=(10, 7))
        bp = ax.boxplot(data_by_type, vert=False, patch_artist=True,
                        positions=range(len(order)),
                        whiskerprops=dict(linewidth=0.9),
                        medianprops=dict(color="white", linewidth=1.8),
                        flierprops=dict(marker=".", markersize=2, alpha=0.4))
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.75)

        ax.axvline(0, color="0.3", lw=1.0, ls="--")
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels(order, fontsize=9)
        ax.set_title("EVI Trend Slope by Forest Type (2000–2024)",
                     fontweight="bold")
        ax.set_xlabel("Theil–Sen slope (EVI yr⁻¹)", labelpad=4)
        ax.legend(
            handles=[mpatches.Patch(color=_TREND_PALETTE["Greening"], alpha=0.75,
                                    label="Positive median (greening)"),
                     mpatches.Patch(color=_TREND_PALETTE["Browning"], alpha=0.75,
                                    label="Negative median (browning)")],
            fontsize=9, loc="lower right", framealpha=0.9)
        fig.tight_layout()
        save_plot(fig, out_path)


def _plot_slope_vs_richness_sci(df: pd.DataFrame, out_path) -> None:
    """2-panel scatter: slope ~ richness and slope ~ SCI with regression lines."""
    pairs = [
        ("richness", "Species richness (S)", "YlGn"),
        ("sci_index", "Stratification Complexity Index (SCI)", "RdYlGn"),
    ]
    pairs = [(col, lbl, cmap) for col, lbl, cmap in pairs if col in df.columns]
    if not pairs:
        return

    with pub_style(font_size=11):
        fig, axes = plt.subplots(1, len(pairs), figsize=(6 * len(pairs), 6))
        if len(pairs) == 1:
            axes = [axes]

        for ax, (col, xlabel, cmap) in zip(axes, pairs):
            sub = df.dropna(subset=["sen_slope", col])
            sc = ax.scatter(sub[col], sub["sen_slope"],
                            c=sub["elevation"], cmap="terrain",
                            s=10, alpha=0.5, linewidths=0,
                            rasterized=True, zorder=2)
            cb = fig.colorbar(sc, ax=ax, shrink=0.75, pad=0.02)
            cb.set_label("Elevation (m)", fontsize=9)
            cb.ax.tick_params(labelsize=8)

            # Regression line
            r, p = stats.pearsonr(sub[col], sub["sen_slope"])
            m, b = np.polyfit(sub[col], sub["sen_slope"], 1)
            x_range = np.linspace(sub[col].min(), sub[col].max(), 200)
            ax.plot(x_range, m * x_range + b,
                    color="#C0392B", lw=2.0, zorder=5)

            p_str = "p < 0.001" if p < 0.001 else f"p = {p:.3f}"
            ax.annotate(f"r = {r:.3f},  {p_str}\nn = {len(sub):,}",
                        xy=(0.03, 0.97), xycoords="axes fraction",
                        va="top", fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                                  edgecolor="0.6", alpha=0.92))

            ax.axhline(0, color="0.4", lw=0.9, ls="--")
            ax.set_xlabel(xlabel, labelpad=4)
            ax.set_ylabel("EVI slope (EVI yr⁻¹)", labelpad=4)
            ax.set_title(f"EVI Slope vs {xlabel.split('(')[0].strip()}",
                         fontweight="bold")

        fig.suptitle("EVI Trend vs Biodiversity Indicators — NFI Plots",
                     fontsize=13, fontweight="bold")
        fig.tight_layout()
        save_plot(fig, out_path)


def _plot_spatial_trend_map(sen_path, mk_path, boundary, master: pd.DataFrame,
                             out_path, sig: float = 0.05) -> None:
    """Spatial map: classify every pixel as Greening / Browning / Stable."""
    import rasterio

    with rasterio.open(sen_path) as src:
        slope_arr = src.read(1).astype(float)
        slope_arr[~np.isfinite(slope_arr)] = np.nan
        extent = [src.bounds.left, src.bounds.right,
                  src.bounds.bottom, src.bounds.top]

    with rasterio.open(mk_path) as src:
        tau_arr2  = src.read(1).astype(float)
        pval_raw2 = src.read(2).astype(float)
    pval_arr = (pval_raw2 if np.any(np.isfinite(pval_raw2))
                else _mk_tau_to_pvalue(tau_arr2, n=25))
    pval_arr[~np.isfinite(pval_arr)] = np.nan

    # Classification: 1=Greening, -1=Browning, 0=Stable, NaN=nodata
    cls_arr = np.full(slope_arr.shape, np.nan)
    valid = np.isfinite(slope_arr) & np.isfinite(pval_arr)
    cls_arr[valid & (pval_arr <= sig) & (slope_arr > 0)] = 1
    cls_arr[valid & (pval_arr <= sig) & (slope_arr < 0)] = -1
    cls_arr[valid & (pval_arr > sig)]                     = 0

    # Count pixel classes
    n_green  = int(np.sum(cls_arr == 1))
    n_brown  = int(np.sum(cls_arr == -1))
    n_stable = int(np.sum(cls_arr == 0))
    n_total  = n_green + n_brown + n_stable

    # RGB image
    h, w = cls_arr.shape
    rgb = np.ones((h, w, 4), dtype=np.float32)  # white default
    rgb[cls_arr == 1]  = mpatches.colors.to_rgba("#1B7837", alpha=0.85)
    rgb[cls_arr == -1] = mpatches.colors.to_rgba("#8C510A", alpha=0.85)
    rgb[cls_arr == 0]  = mpatches.colors.to_rgba("#CCCCCC", alpha=0.60)
    rgb[np.isnan(cls_arr)] = [1, 1, 1, 0]  # transparent

    with pub_style(font_size=11):
        fig, ax = plt.subplots(figsize=(11, 8))
        ax.imshow(rgb, extent=extent, origin="upper", aspect="auto", zorder=1)

        if boundary is not None:
            try:
                boundary.boundary.plot(ax=ax, color="0.2", linewidth=0.9, zorder=3)
            except Exception:
                pass

        # NFI plot dots (small, white outline)
        loc = master.dropna(subset=["longitude", "latitude"])
        ax.scatter(loc["longitude"], loc["latitude"],
                   color="white", edgecolors="0.3", s=5,
                   alpha=0.7, linewidths=0.4, rasterized=True, zorder=4)

        # Legend
        ax.legend(
            handles=[
                mpatches.Patch(color="#1B7837", alpha=0.85,
                               label=f"Significant greening  ({n_green/n_total*100:.1f}% of area)"),
                mpatches.Patch(color="#8C510A", alpha=0.85,
                               label=f"Significant browning  ({n_brown/n_total*100:.1f}% of area)"),
                mpatches.Patch(color="#CCCCCC", alpha=0.75,
                               label=f"Stable / non-significant  ({n_stable/n_total*100:.1f}%)"),
                mpatches.Patch(color="white", edgecolor="0.4",
                               label=f"NFI plots (n={len(loc):,})"),
            ],
            loc="lower left", framealpha=0.93, edgecolor="0.7", fontsize=9,
        )

        ax.set_title(
            f"Spatial EVI Trend Classification — Bhutan  (MODIS 250 m, 2000–2024, MK p ≤ {sig})",
            fontweight="bold", fontsize=12, pad=10)
        ax.set_xlabel("Longitude (°E)", labelpad=4)
        ax.set_ylabel("Latitude (°N)", labelpad=4)
        ax.tick_params(labelsize=10)
        fig.tight_layout()
        save_plot(fig, out_path)


def _plot_integrated_panel(df: pd.DataFrame, sen_path, mk_path,
                            boundary, out_path, sig: float = 0.05) -> None:
    """4-panel publication figure: spatial map + elevation + forest type + richness."""
    import rasterio

    # ── Prepare data ──────────────────────────────────────────────────────────
    with rasterio.open(sen_path) as src:
        slope_arr = src.read(1).astype(float)
        slope_arr[~np.isfinite(slope_arr)] = np.nan
        map_extent = [src.bounds.left, src.bounds.right,
                      src.bounds.bottom, src.bounds.top]
    with rasterio.open(mk_path) as src:
        tau_arr3  = src.read(1).astype(float)
        pval_raw3 = src.read(2).astype(float)
    pval_arr = (pval_raw3 if np.any(np.isfinite(pval_raw3))
                else _mk_tau_to_pvalue(tau_arr3, n=25))
    pval_arr[~np.isfinite(pval_arr)] = np.nan

    cls_arr = np.full(slope_arr.shape, np.nan)
    valid = np.isfinite(slope_arr) & np.isfinite(pval_arr)
    cls_arr[valid & (pval_arr <= sig) & (slope_arr > 0)] = 1
    cls_arr[valid & (pval_arr <= sig) & (slope_arr < 0)] = -1
    cls_arr[valid & (pval_arr > sig)] = 0

    h, w = cls_arr.shape
    rgb = np.ones((h, w, 4), dtype=np.float32)
    rgb[cls_arr == 1]  = mpatches.colors.to_rgba("#1B7837", alpha=0.85)
    rgb[cls_arr == -1] = mpatches.colors.to_rgba("#8C510A", alpha=0.85)
    rgb[cls_arr == 0]  = mpatches.colors.to_rgba("#CCCCCC", alpha=0.60)
    rgb[np.isnan(cls_arr)] = [1, 1, 1, 0]

    # Elevation band means + CI
    sub_e = df.dropna(subset=["sen_slope", "elev_band"])
    elev_stats = (sub_e.groupby("elev_band", observed=True)["sen_slope"]
                  .agg(["mean", "std", "count"]).reset_index())
    elev_stats["se"] = elev_stats["std"] / np.sqrt(elev_stats["count"])

    # Forest type medians (top 10 by count)
    sub_f = df.dropna(subset=["sen_slope", "forest_type"])
    ft_order = (sub_f.groupby("forest_type")["sen_slope"]
                .median().sort_values().index.tolist())

    with pub_style(font_size=10):
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(2, 2, hspace=0.38, wspace=0.30,
                              left=0.06, right=0.97, top=0.93, bottom=0.07)
        ax_map  = fig.add_subplot(gs[0, 0])
        ax_elev = fig.add_subplot(gs[0, 1])
        ax_ft   = fig.add_subplot(gs[1, 0])
        ax_rich = fig.add_subplot(gs[1, 1])

        # ── A: Spatial map ────────────────────────────────────────────────────
        ax_map.imshow(rgb, extent=map_extent, origin="upper",
                      aspect="auto", zorder=1)
        if boundary is not None:
            try:
                boundary.boundary.plot(ax=ax_map, color="0.2",
                                       linewidth=0.8, zorder=3)
            except Exception:
                pass
        loc = df.dropna(subset=["longitude", "latitude"])
        ax_map.scatter(loc["longitude"], loc["latitude"],
                       color="white", edgecolors="0.35", s=3,
                       linewidths=0.3, alpha=0.6, rasterized=True, zorder=4)
        n_g = int(np.sum(cls_arr == 1))
        n_b = int(np.sum(cls_arr == -1))
        n_s = int(np.sum(cls_arr == 0))
        n_tot = n_g + n_b + n_s
        ax_map.legend(
            handles=[
                mpatches.Patch(color="#1B7837", alpha=0.85,
                               label=f"Greening ({n_g/n_tot*100:.0f}%)"),
                mpatches.Patch(color="#8C510A", alpha=0.85,
                               label=f"Browning ({n_b/n_tot*100:.0f}%)"),
                mpatches.Patch(color="#CCCCCC", alpha=0.7,
                               label=f"Stable ({n_s/n_tot*100:.0f}%)"),
            ],
            loc="lower left", fontsize=8, framealpha=0.92)
        ax_map.set_title("(a) Spatial EVI Trend Classification",
                         fontweight="bold", fontsize=11)
        ax_map.set_xlabel("Longitude (°E)", labelpad=3)
        ax_map.set_ylabel("Latitude (°N)", labelpad=3)
        ax_map.tick_params(labelsize=9)

        # ── B: Elevation band bar chart ───────────────────────────────────────
        bar_colors = [_TREND_PALETTE["Greening"] if m > 0 else _TREND_PALETTE["Browning"]
                      for m in elev_stats["mean"]]
        ax_elev.barh(range(len(elev_stats)), elev_stats["mean"],
                     xerr=elev_stats["se"] * 1.96, color=bar_colors,
                     alpha=0.80, height=0.65, capsize=3,
                     error_kw=dict(elinewidth=0.8, ecolor="0.3"))
        ax_elev.axvline(0, color="0.3", lw=1.0, ls="--")
        ax_elev.set_yticks(range(len(elev_stats)))
        ax_elev.set_yticklabels(
            [f"{lb}  (n={n:,})"
             for lb, n in zip(elev_stats["elev_band"], elev_stats["count"])],
            fontsize=8.5)
        ax_elev.set_title("(b) EVI Slope by Elevation Band",
                          fontweight="bold", fontsize=11)
        ax_elev.set_xlabel("Mean Theil–Sen slope ± 95% CI (EVI yr⁻¹)", labelpad=3)

        # ── C: Forest type box plots ──────────────────────────────────────────
        data_by_type = [sub_f.loc[sub_f["forest_type"] == ft, "sen_slope"].values
                        for ft in ft_order]
        medians = [np.nanmedian(d) for d in data_by_type]
        ft_colors = [_TREND_PALETTE["Greening"] if m > 0 else _TREND_PALETTE["Browning"]
                     for m in medians]
        bp = ax_ft.boxplot(data_by_type, vert=False, patch_artist=True,
                           positions=range(len(ft_order)),
                           whiskerprops=dict(linewidth=0.8),
                           medianprops=dict(color="white", linewidth=1.6),
                           flierprops=dict(marker=".", markersize=2, alpha=0.3))
        for patch, color in zip(bp["boxes"], ft_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.78)
        ax_ft.axvline(0, color="0.3", lw=1.0, ls="--")
        ax_ft.set_yticks(range(len(ft_order)))
        ax_ft.set_yticklabels(ft_order, fontsize=8.5)
        ax_ft.set_title("(c) EVI Slope by Forest Type",
                        fontweight="bold", fontsize=11)
        ax_ft.set_xlabel("Theil–Sen slope (EVI yr⁻¹)", labelpad=3)

        # ── D: Slope vs richness ──────────────────────────────────────────────
        sub_r = df.dropna(subset=["sen_slope", "richness"])
        sc = ax_rich.scatter(sub_r["richness"], sub_r["sen_slope"],
                             c=sub_r["elevation"], cmap="terrain",
                             s=8, alpha=0.45, linewidths=0,
                             rasterized=True, zorder=2)
        cb = fig.colorbar(sc, ax=ax_rich, shrink=0.75, pad=0.02)
        cb.set_label("Elevation (m)", fontsize=9)
        cb.ax.tick_params(labelsize=8)
        r, p = stats.pearsonr(sub_r["richness"], sub_r["sen_slope"])
        m, b = np.polyfit(sub_r["richness"], sub_r["sen_slope"], 1)
        xr = np.linspace(sub_r["richness"].min(), sub_r["richness"].max(), 200)
        ax_rich.plot(xr, m * xr + b, color="#C0392B", lw=2.0, zorder=5)
        p_str = "p < 0.001" if p < 0.001 else f"p = {p:.3f}"
        ax_rich.annotate(f"r = {r:.3f},  {p_str}",
                         xy=(0.03, 0.97), xycoords="axes fraction",
                         va="top", fontsize=10,
                         bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                                   edgecolor="0.6", alpha=0.92))
        ax_rich.axhline(0, color="0.4", lw=0.9, ls="--")
        ax_rich.set_xlabel("Species richness (S)", labelpad=3)
        ax_rich.set_ylabel("EVI slope (EVI yr⁻¹)", labelpad=3)
        ax_rich.set_title("(d) EVI Slope vs Species Richness",
                          fontweight="bold", fontsize=11)

        fig.suptitle(
            "EVI Trend Analysis — Bhutan NFI Plots  |  MODIS MOD13Q1 250 m  |  2000–2024",
            fontsize=13, fontweight="bold")
        save_plot(fig, out_path)


# ── module entry ──────────────────────────────────────────────────────────────

def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root   = ensure_dirs("08b_evi_spatial", config)
    out_plots  = out_root / "plots"
    out_tables = out_root / "tables"
    warn_list  = []
    outputs    = []

    # ── Input raster paths ────────────────────────────────────────────────────
    evi_dir        = config["paths"]["inputs"]["evi_modis_dir"]
    sen_path       = evi_dir / "Bhutan_EVI_TheilSenSlope_2000_2024.tif"
    mk_path        = evi_dir / "Bhutan_EVI_MannKendall_tau_p_2000_2024.tif"
    evi_stack_path = evi_dir / "Bhutan_MOD13Q1_EVI_AnnualMean_2000_2024_STACK_QA.tif"

    check_file(sen_path, "Theil-Sen slope raster", required=True)
    check_file(mk_path,  "Mann-Kendall raster",    required=True)

    # ── Load NFI plot master table ────────────────────────────────────────────
    alpha_path = (config["output"]["module_dirs"]["03_alpha_diversity"]
                  / "tables" / "alpha_diversity_summary.csv")
    sci_path   = (config["output"]["module_dirs"]["09_sci_index"]
                  / "tables" / "stratification_complexity_index.csv")
    check_file(alpha_path, "Alpha diversity summary", required=True)

    alpha = pd.read_csv(alpha_path)
    required_cols = {"plot_id", "longitude", "latitude", "richness",
                     "elevation", "forest_type"}
    if not required_cols.issubset(alpha.columns):
        raise RuntimeError(
            f"Alpha diversity table missing: {required_cols - set(alpha.columns)}")

    master = alpha[["plot_id", "longitude", "latitude", "richness",
                    "elevation", "forest_type", "shannon", "simpson"]].copy()
    if sci_path.exists():
        sci = pd.read_csv(sci_path)
        if {"plot_id", "sci_index"}.issubset(sci.columns):
            master = master.merge(sci[["plot_id", "sci_index"]],
                                  on="plot_id", how="left")
        else:
            warn_list.append("SCI table found but missing plot_id/sci_index columns.")
    else:
        warn_list.append("SCI table not found; sci_index column will be absent.")

    # ── Sample rasters at plot coordinates ────────────────────────────────────
    coords = list(zip(master["longitude"], master["latitude"]))

    master["sen_slope"] = _sample_raster(sen_path, coords, band=1)
    master["mk_tau"]    = _sample_raster(mk_path,  coords, band=1)
    # Band 2 (p-value) may be absent from GEE export; derive analytically from tau.
    raw_mkp = _sample_raster(mk_path, coords, band=2)
    if np.all(np.isnan(raw_mkp)):
        warn_list.append(
            "MK p-value band is all NaN in exported raster; "
            "p-values computed analytically from MK tau (n=25, normal approximation)."
        )
        master["mk_p"] = _mk_tau_to_pvalue(master["mk_tau"].values, n=25)
    else:
        master["mk_p"] = raw_mkp

    if evi_stack_path.exists():
        mean_evi, evi_2000, evi_2024 = _sample_stack_mean(evi_stack_path, coords)
        master["mean_evi_2000_2024"] = mean_evi
        master["evi_2000"]           = evi_2000
        master["evi_2024"]           = evi_2024
    else:
        warn_list.append("EVI annual stack not found; mean EVI columns will be absent.")

    # ── Classify per-plot trend ───────────────────────────────────────────────
    master["trend_class"] = [
        _classify_pixel(s, p)
        for s, p in zip(master["sen_slope"], master["mk_p"])
    ]
    master["elev_band"] = pd.cut(
        master["elevation"],
        bins=_ELEV_BINS, labels=_ELEV_LABELS, right=False,
    )

    # ── Per-plot table ────────────────────────────────────────────────────────
    out_plot_tbl = out_tables / "plot_evi_trends.csv"
    master.to_csv(out_plot_tbl, index=False)
    outputs.append(str(out_plot_tbl))

    # ── Elevation band summary ────────────────────────────────────────────────
    elev_grp = (master.dropna(subset=["sen_slope", "elev_band"])
                .groupby("elev_band", observed=True))
    elev_summary = elev_grp["sen_slope"].agg(
        n="count", mean="mean", median="median", std="std",
        pct_greening=lambda x: (x > 0).mean() * 100,
        pct_sig_greening=lambda x: (
            (x > 0) &
            (master.loc[x.index, "mk_p"] <= 0.05)
        ).mean() * 100,
    ).reset_index()
    out_elev = out_tables / "evi_by_elevation_band.csv"
    elev_summary.to_csv(out_elev, index=False)
    outputs.append(str(out_elev))

    # ── Forest type summary ───────────────────────────────────────────────────
    ft_grp = (master.dropna(subset=["sen_slope", "forest_type"])
              .groupby("forest_type"))
    ft_summary = ft_grp["sen_slope"].agg(
        n="count", mean="mean", median="median", std="std",
        pct_greening=lambda x: (x > 0).mean() * 100,
    ).reset_index().sort_values("median", ascending=False)
    out_ft = out_tables / "evi_by_forest_type.csv"
    ft_summary.to_csv(out_ft, index=False)
    outputs.append(str(out_ft))

    # ── Pixel-level area statistics ───────────────────────────────────────────
    try:
        import rasterio
        with rasterio.open(sen_path) as src:
            slope_arr = src.read(1).astype(float)
            slope_arr[~np.isfinite(slope_arr)] = np.nan
            pixel_area_km2 = abs(src.res[0] * src.res[1]) * (111_320 ** 2) / 1e6

        with rasterio.open(mk_path) as src:
            tau_arr = src.read(1).astype(float)
            pval_raw = src.read(2).astype(float)

        # Use analytical p-value if band 2 is absent
        if not np.any(np.isfinite(pval_raw)):
            pval_arr = _mk_tau_to_pvalue(tau_arr, n=25)
        else:
            pval_arr = pval_raw
        pval_arr[~np.isfinite(pval_arr)] = np.nan

        valid_mask = np.isfinite(slope_arr) & np.isfinite(pval_arr)
        n_valid = int(valid_mask.sum())
        n_green = int(((slope_arr > 0) & (pval_arr <= 0.05) & valid_mask).sum())
        n_brown = int(((slope_arr < 0) & (pval_arr <= 0.05) & valid_mask).sum())
        n_stable = n_valid - n_green - n_brown
        area_stats = pd.DataFrame([{
            "category": "Significant greening (p≤0.05)",
            "n_pixels": n_green,
            "area_km2": round(n_green * pixel_area_km2, 1),
            "pct_valid_area": round(n_green / n_valid * 100, 2),
        }, {
            "category": "Significant browning (p≤0.05)",
            "n_pixels": n_brown,
            "area_km2": round(n_brown * pixel_area_km2, 1),
            "pct_valid_area": round(n_brown / n_valid * 100, 2),
        }, {
            "category": "Stable / non-significant",
            "n_pixels": n_stable,
            "area_km2": round(n_stable * pixel_area_km2, 1),
            "pct_valid_area": round(n_stable / n_valid * 100, 2),
        }, {
            "category": "Total valid",
            "n_pixels": n_valid,
            "area_km2": round(n_valid * pixel_area_km2, 1),
            "pct_valid_area": 100.0,
        }])
        out_area = out_tables / "evi_area_stats.csv"
        area_stats.to_csv(out_area, index=False)
        outputs.append(str(out_area))
    except Exception as exc:
        warn_list.append(f"Pixel-level area stats failed: {type(exc).__name__}: {exc}")

    # ── Load boundary for spatial plots ──────────────────────────────────────
    boundary = None
    try:
        import geopandas as gpd
        bnd_path = config["paths"]["inputs"]["bhutan_boundary"]
        if bnd_path.exists():
            boundary = gpd.read_file(bnd_path).to_crs(
                epsg=config["params"]["crs_epsg"])
    except Exception as exc:
        warn_list.append(f"Boundary load failed: {type(exc).__name__}: {exc}")

    # ── Plots ─────────────────────────────────────────────────────────────────
    try:
        p = out_plots / "evi_slope_vs_elevation.png"
        _plot_slope_vs_elevation(master, p)
        outputs.append(str(p))
    except Exception as exc:
        warn_list.append(f"Slope vs elevation plot failed: {exc}")

    try:
        p = out_plots / "evi_slope_by_forest_type.png"
        _plot_slope_by_forest_type(master, p)
        outputs.append(str(p))
    except Exception as exc:
        warn_list.append(f"Slope by forest type plot failed: {exc}")

    try:
        p = out_plots / "evi_slope_vs_richness_sci.png"
        _plot_slope_vs_richness_sci(master, p)
        outputs.append(str(p))
    except Exception as exc:
        warn_list.append(f"Slope vs richness/SCI plot failed: {exc}")

    try:
        p = out_plots / "evi_spatial_trend_map.png"
        _plot_spatial_trend_map(sen_path, mk_path, boundary, master, p)
        outputs.append(str(p))
    except Exception as exc:
        warn_list.append(f"Spatial trend map failed: {exc}")

    try:
        p = out_plots / "evi_integrated_panel.png"
        _plot_integrated_panel(master, sen_path, mk_path, boundary, p)
        outputs.append(str(p))
    except Exception as exc:
        warn_list.append(f"Integrated panel plot failed: {exc}")

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warn_list,
        "runtime_sec": time.time() - t0,
    }
