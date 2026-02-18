from __future__ import annotations

import time
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, theilslopes

from python.utils import check_file, ensure_dirs, normalize_name, pub_style, save_plot


def _calc_trend(df: pd.DataFrame, value_col: str, time_col: str, min_time_points: int) -> dict:
    x = pd.to_numeric(df[value_col], errors="coerce")
    t = pd.to_numeric(df[time_col], errors="coerce")
    ok = x.notna() & t.notna()
    x = x[ok]
    t = t[ok]
    if len(x) < min_time_points:
        return {"theil_sen_slope": np.nan, "mk_p_value": np.nan, "n_obs": int(len(x))}
    slope, _, _, _ = theilslopes(x, t)
    _, p = kendalltau(t, x)
    return {"theil_sen_slope": float(slope), "mk_p_value": float(p), "n_obs": int(len(x))}


def _classify_trend(slope: float, pval: float) -> str:
    if pd.notna(pval) and pval <= 0.05 and pd.notna(slope):
        if slope > 0:
            return "Greening"
        if slope < 0:
            return "Browning"
    return "Stable"


def _load_plot_points_table(config: dict) -> pd.DataFrame | None:
    gpkg = config["paths"]["canonical"]["plot_points_gpkg"]
    if gpkg.exists():
        try:
            import geopandas as gpd

            pts = gpd.read_file(gpkg)
            df = pts.drop(columns="geometry", errors="ignore")
            if {"plot_id", "longitude", "latitude"}.issubset(df.columns):
                return df[["plot_id", "longitude", "latitude"]].copy()
        except Exception:
            pass
    csv_path = config["paths"]["compatibility"]["plot_coordinates_cleaned_csv"]
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if {"plot_id", "longitude", "latitude"}.issubset(df.columns):
            return df[["plot_id", "longitude", "latitude"]].copy()
    return None


def _extract_lon_lat_from_geo_col(evi: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    lon = pd.Series([np.nan] * len(evi), index=evi.index, dtype=float)
    lat = pd.Series([np.nan] * len(evi), index=evi.index, dtype=float)
    geo_col = next((c for c in evi.columns if normalize_name(c) == "geo"), None)
    if geo_col is None:
        return lon, lat
    for i, val in evi[geo_col].items():
        try:
            obj = json.loads(val) if isinstance(val, str) else val
            if not isinstance(obj, dict):
                continue
            typ = str(obj.get("type", "")).lower()
            coords = obj.get("coordinates")
            if typ == "point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                lon.at[i] = float(coords[0])
                lat.at[i] = float(coords[1])
            elif typ == "multipoint" and isinstance(coords, list) and len(coords) > 0:
                c0 = coords[0]
                if isinstance(c0, (list, tuple)) and len(c0) >= 2:
                    lon.at[i] = float(c0[0])
                    lat.at[i] = float(c0[1])
        except Exception:
            continue
    return lon, lat


def _plot_evi_timeseries_national(
    evi: pd.DataFrame,
    date_col: str,
    evi_col: str,
    trend: dict,
    out_path,
) -> None:
    """3-panel publication-quality EVI time series figure for national-aggregate data.

    Panels:
      Top (full width): bi-weekly scatter + annual mean + Theil-Sen trend line.
      Bottom-left: monthly climatology (mean ± 1 SD bar chart).
      Bottom-right: annual EVI anomaly bar chart.
    """
    import matplotlib.dates as mdates
    import matplotlib.patches as mpatches
    import matplotlib.ticker as mticker

    # ── Prepare data ──────────────────────────────────────────────────────────
    df = evi[[date_col, evi_col]].copy()
    df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["_evi"] = pd.to_numeric(df[evi_col], errors="coerce")
    df = df.dropna(subset=["_date", "_evi"]).sort_values("_date").reset_index(drop=True)

    df["_year"] = df["_date"].dt.year
    df["_month"] = df["_date"].dt.month

    annual = df.groupby("_year")["_evi"].mean().reset_index()
    annual["_date"] = pd.to_datetime(annual["_year"].astype(str) + "-07-01")

    clim = df.groupby("_month")["_evi"].agg(["mean", "std"]).reset_index()
    MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # ── Trend line (Theil-Sen in ordinal-day units) ───────────────────────────
    t_ord = df["_date"].map(lambda d: d.toordinal())
    slope_day, intercept, _, _ = theilslopes(df["_evi"].values, t_ord.values)
    slope_yr = slope_day * 365.25          # EVI units per year

    t_lo, t_hi = t_ord.min(), t_ord.max()
    t_range = np.linspace(t_lo, t_hi, 500)
    d_range = [pd.Timestamp.fromordinal(int(t)) for t in t_range]
    y_trend = intercept + slope_day * t_range

    # ── Annual anomaly ────────────────────────────────────────────────────────
    global_mean = df["_evi"].mean()
    annual["_anom"] = annual["_evi"] - global_mean
    anom_colors = ["#1B7837" if v >= 0 else "#8C510A" for v in annual["_anom"]]

    # ── Statistics annotation text ────────────────────────────────────────────
    p_val = trend.get("mk_p_value", np.nan)
    n_obs = trend.get("n_obs", len(df))
    p_str = "p < 0.001" if (pd.notna(p_val) and p_val < 0.001) else f"p = {p_val:.3f}"
    trend_class = trend.get("trend_class", _classify_trend(slope_yr, p_val))
    delta = slope_yr * (annual["_year"].max() - annual["_year"].min())
    ann_text = (
        f"Theil–Sen slope:  {slope_yr:+.2f} EVI yr⁻¹\n"
        f"Mann–Kendall:  {p_str}\n"
        f"Net change (2000–2024):  {delta:+.0f} EVI\n"
        f"Trend class:  {trend_class}  |  n = {n_obs:,} obs"
    )

    # ── Figure layout ─────────────────────────────────────────────────────────
    with pub_style(font_size=11):
        fig = plt.figure(figsize=(14, 9))
        gs = fig.add_gridspec(
            2, 2,
            height_ratios=[2.4, 1],
            hspace=0.38, wspace=0.28,
            left=0.07, right=0.97, top=0.93, bottom=0.08,
        )
        ax_ts   = fig.add_subplot(gs[0, :])   # top: full time series
        ax_clim = fig.add_subplot(gs[1, 0])   # bottom-left: seasonality
        ax_ann  = fig.add_subplot(gs[1, 1])   # bottom-right: annual anomaly

        # ── Panel 1: time series ──────────────────────────────────────────────
        # Monsoon shading (Jun–Sep)
        for yr in sorted(df["_year"].unique()):
            ax_ts.axvspan(
                pd.Timestamp(f"{yr}-06-01"), pd.Timestamp(f"{yr}-09-30"),
                color="#AED6F1", alpha=0.13, linewidth=0, zorder=0,
            )

        # Raw bi-weekly scatter
        ax_ts.scatter(
            df["_date"], df["_evi"],
            color="#95CA7B", s=14, alpha=0.50, linewidths=0,
            label="Bi-weekly EVI", zorder=2,
        )

        # Annual mean line
        ax_ts.plot(
            annual["_date"], annual["_evi"],
            color="#1B7837", lw=2.2, marker="o", ms=4.5, zorder=4,
            label="Annual mean EVI",
        )

        # Theil-Sen trend line
        ax_ts.plot(
            d_range, y_trend,
            color="#C0392B", lw=2.0, ls="--", zorder=5,
            label="Theil–Sen trend",
        )

        # Annotation box (top-left)
        ax_ts.annotate(
            ann_text,
            xy=(0.01, 0.97), xycoords="axes fraction",
            va="top", ha="left", fontsize=9.5,
            bbox=dict(
                boxstyle="round,pad=0.45",
                facecolor="white", edgecolor="0.65", alpha=0.94,
            ),
            zorder=7,
        )

        # Monsoon label (top-right corner)
        ax_ts.text(
            0.99, 0.97,
            "Light blue shading: monsoon season (Jun–Sep)",
            transform=ax_ts.transAxes,
            fontsize=8.5, color="#2471A3",
            va="top", ha="right",
        )

        ax_ts.set_title(
            "National Forest EVI Trend (2000–2024) — Bhutan  (MODIS MOD13Q1, 16-day composite)",
            fontweight="bold", fontsize=12, pad=8,
        )
        ax_ts.set_xlabel("Year", labelpad=4)
        ax_ts.set_ylabel("EVI (MODIS raw units, ×10⁻⁴ = true EVI)", labelpad=6)
        ax_ts.xaxis.set_major_locator(mdates.YearLocator(2))
        ax_ts.xaxis.set_minor_locator(mdates.YearLocator(1))
        ax_ts.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax_ts.tick_params(axis="x", which="major", labelrotation=0, labelsize=10)
        ax_ts.tick_params(axis="y", labelsize=10)
        ax_ts.legend(loc="lower right", framealpha=0.92, fontsize=9.5, edgecolor="0.7")

        # ── Panel 2: monthly climatology ──────────────────────────────────────
        clim_colors = [
            "#2E86AB" if m in [6, 7, 8, 9] else "#66A355"
            for m in clim["_month"]
        ]
        bars = ax_clim.bar(
            clim["_month"], clim["mean"],
            yerr=clim["std"], capsize=3.5,
            color=clim_colors, width=0.72, zorder=3,
            error_kw=dict(elinewidth=0.9, ecolor="0.35"),
        )
        ax_clim.set_xticks(range(1, 13))
        ax_clim.set_xticklabels(MONTH_ABBR, fontsize=8.5)
        ax_clim.set_title("Seasonal Climatology", fontweight="bold", fontsize=11)
        ax_clim.set_xlabel("Month", labelpad=4)
        ax_clim.set_ylabel("Mean EVI ± 1 SD", labelpad=4)
        ax_clim.tick_params(labelsize=9)
        # Legend patches: monsoon vs dry
        ax_clim.legend(
            handles=[
                mpatches.Patch(color="#2E86AB", label="Monsoon (Jun–Sep)"),
                mpatches.Patch(color="#66A355", label="Other months"),
            ],
            fontsize=8, loc="upper left", framealpha=0.88,
        )

        # ── Panel 3: annual anomaly ───────────────────────────────────────────
        ax_ann.bar(annual["_year"], annual["_anom"], color=anom_colors, width=0.75, zorder=3)
        ax_ann.axhline(0, color="0.35", lw=1.0)
        ax_ann.set_title("Annual EVI Anomaly", fontweight="bold", fontsize=11)
        ax_ann.set_xlabel("Year", labelpad=4)
        ax_ann.set_ylabel("EVI anomaly (relative to 2000–2024 mean)", labelpad=4)
        ax_ann.xaxis.set_major_locator(mticker.MultipleLocator(4))
        ax_ann.tick_params(axis="x", labelrotation=45, labelsize=8.5)
        ax_ann.tick_params(axis="y", labelsize=9)
        ax_ann.legend(
            handles=[
                mpatches.Patch(color="#1B7837", label="Above mean"),
                mpatches.Patch(color="#8C510A", label="Below mean"),
            ],
            fontsize=8, loc="upper left", framealpha=0.88,
        )

        fig.suptitle(
            "Bhutan National Forest EVI Trend Analysis  |  Theil–Sen / Mann–Kendall",
            fontsize=13, fontweight="bold", y=0.985,
        )

        save_plot(fig, out_path)


def _save_trend_map(map_df: pd.DataFrame, out_map, palette: dict) -> None:
    counts = map_df["trend_class"].value_counts()
    with pub_style():
        fig, ax = plt.subplots(figsize=(8, 6))
        for cls, sub in map_df.groupby("trend_class", dropna=False):
            n = counts.get(cls, 0)
            ax.scatter(
                sub["longitude"], sub["latitude"],
                color=palette.get(str(cls), "#BAB0AC"),
                s=8, alpha=0.75, linewidths=0,
                label=f"{cls} (n={n:,})",
                rasterized=True,
            )
        ax.legend(title="EVI trend class", framealpha=0.9, edgecolor="0.8",
                  fontsize=9, loc="lower right")
        ax.set_title("Vegetation Greenness Trend Classes (EVI)\nTheil–Sen slope, Mann–Kendall p ≤ 0.05")
        ax.set_xlabel("Longitude (°E)")
        ax.set_ylabel("Latitude (°N)")
        ax.tick_params(labelsize=9)
        fig.tight_layout()
        save_plot(fig, out_map)


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_root = ensure_dirs("08_evi_trends", config)
    out_plots = out_root / "plots"
    out_tables = out_root / "tables"

    check_file(config["paths"]["inputs"]["evi_csv"], "EVI CSV", required=True)
    evi = pd.read_csv(config["paths"]["inputs"]["evi_csv"])

    norm = {normalize_name(c): c for c in evi.columns}
    id_col = norm.get("plotid")
    year_col = norm.get("year")
    month_col = norm.get("month")
    date_col = norm.get("date")
    evi_col = norm.get("evi")
    lon_col = next((norm.get(k) for k in ["longitude", "lon", "x"] if norm.get(k) is not None), None)
    lat_col = next((norm.get(k) for k in ["latitude", "lat", "y"] if norm.get(k) is not None), None)

    if evi_col is None:
        raise RuntimeError("EVI column was not detected in EVI CSV.")

    out_table = out_tables / "evi_trend_analysis.csv"
    out_map = out_plots / "evi_trend_spatial_map.png"
    warnings = []

    if id_col and (date_col or (year_col and month_col)):
        if date_col:
            evi["..time"] = pd.to_datetime(evi[date_col], errors="coerce").map(lambda d: d.toordinal() if pd.notna(d) else np.nan)
        else:
            evi["..time"] = pd.to_numeric(evi[year_col], errors="coerce") + (pd.to_numeric(evi[month_col], errors="coerce") - 1) / 12

        rows = []
        for pid, sub in evi.groupby(id_col):
            res = _calc_trend(sub, evi_col, "..time", config["params"]["min_time_points"])
            rows.append({"plot_id": str(pid), **res})

        trend_tbl = pd.DataFrame(rows)
        trend_tbl["trend_class"] = [ _classify_trend(s, p) for s, p in zip(trend_tbl["theil_sen_slope"], trend_tbl["mk_p_value"]) ]
        trend_tbl.to_csv(out_table, index=False)

        pts_df = _load_plot_points_table(config)

        if pts_df is not None and {"longitude", "latitude", "plot_id"}.issubset(pts_df.columns):
            map_df = pts_df.merge(trend_tbl, on="plot_id", how="left")
            _save_trend_map(map_df, out_map, config["colors"]["trend"])
    elif date_col or (year_col and month_col):
        if date_col:
            evi["..time"] = pd.to_datetime(evi[date_col], errors="coerce").map(lambda d: d.toordinal() if pd.notna(d) else np.nan)
        else:
            evi["..time"] = pd.to_numeric(evi[year_col], errors="coerce") + (pd.to_numeric(evi[month_col], errors="coerce") - 1) / 12

        # Attempt coordinate-to-plot assignment if EVI rows contain usable coordinates.
        if lon_col and lat_col:
            evi["..lon"] = pd.to_numeric(evi[lon_col], errors="coerce")
            evi["..lat"] = pd.to_numeric(evi[lat_col], errors="coerce")
        else:
            evi["..lon"], evi["..lat"] = _extract_lon_lat_from_geo_col(evi)

        pts_df = _load_plot_points_table(config)
        assigned_tbl = None
        if pts_df is not None and evi["..lon"].notna().any() and evi["..lat"].notna().any():
            try:
                import geopandas as gpd

                evi_pts = evi[evi["..lon"].notna() & evi["..lat"].notna()].copy()
                g_evi = gpd.GeoDataFrame(
                    evi_pts,
                    geometry=gpd.points_from_xy(evi_pts["..lon"], evi_pts["..lat"]),
                    crs=f"EPSG:{config['params']['crs_epsg']}",
                )
                g_plots = gpd.GeoDataFrame(
                    pts_df.copy(),
                    geometry=gpd.points_from_xy(pts_df["longitude"], pts_df["latitude"]),
                    crs=f"EPSG:{config['params']['crs_epsg']}",
                )
                joined = gpd.sjoin_nearest(g_evi, g_plots[["plot_id", "geometry"]], how="left")
                if "plot_id" in joined.columns and joined["plot_id"].notna().any():
                    rows = []
                    for pid, sub in joined.groupby("plot_id"):
                        res = _calc_trend(sub, evi_col, "..time", config["params"]["min_time_points"])
                        rows.append({"plot_id": str(pid), **res})
                    assigned_tbl = pd.DataFrame(rows)
                    if not assigned_tbl.empty:
                        assigned_tbl["trend_class"] = [
                            _classify_trend(s, p)
                            for s, p in zip(assigned_tbl["theil_sen_slope"], assigned_tbl["mk_p_value"])
                        ]
                        assigned_tbl["trend_unit"] = "plot_assigned_from_coordinates"
            except Exception as exc:
                warnings.append(f"EVI coordinate-to-plot assignment failed: {type(exc).__name__}: {exc}")

        if assigned_tbl is not None and not assigned_tbl.empty:
            assigned_tbl.to_csv(out_table, index=False)
            if pts_df is not None:
                map_df = pts_df.merge(assigned_tbl, on="plot_id", how="left")
                _save_trend_map(map_df, out_map, config["colors"]["trend"])
        else:
            national = _calc_trend(evi, evi_col, "..time", config["params"]["min_time_points"])
            national["trend_class"] = _classify_trend(national["theil_sen_slope"], national["mk_p_value"])
            national["trend_unit"] = "country"
            pd.DataFrame([national]).to_csv(out_table, index=False)
            warnings.append("EVI CSV has no usable plot_id/coordinates for plot-level trends; saved country-level trend.")

            # Publication-quality time series figure (primary output for national-aggregate data).
            out_ts = out_plots / "evi_trend_timeseries.png"
            _evi_ts_date_col = date_col
            if _evi_ts_date_col is None and year_col and month_col:
                # Construct an ISO date column from year + month so the plot function can parse it.
                evi["..isodate"] = (
                    evi[year_col].astype(str).str.zfill(4)
                    + "-"
                    + evi[month_col].astype(str).str.zfill(2)
                    + "-01"
                )
                _evi_ts_date_col = "..isodate"
            if _evi_ts_date_col is not None:
                _plot_evi_timeseries_national(evi, _evi_ts_date_col, evi_col, national, out_ts)

            # Replicate country trend to plot points for workflow continuity (downstream spatial modules).
            if pts_df is not None and not pts_df.empty:
                rep = pts_df[["plot_id", "longitude", "latitude"]].copy()
                rep["theil_sen_slope"] = national["theil_sen_slope"]
                rep["mk_p_value"] = national["mk_p_value"]
                rep["n_obs"] = national["n_obs"]
                rep["trend_class"] = national["trend_class"]
                rep["trend_unit"] = "country_replicated_to_plots"
                rep.to_csv(out_table, index=False)
                warnings.append(
                    "Replicated country-level EVI trend to all plot points for downstream workflow "
                    "continuity. Spatial map suppressed (all points identical — not informative)."
                )
    else:
        raise RuntimeError("EVI CSV does not contain required fields for trend analysis (plot_id+time or date).")

    outputs = [str(out_table)]
    if out_map.with_suffix(".png").exists():
        outputs.append(str(out_map))
    ts_plot = out_plots / "evi_trend_timeseries.png"
    if ts_plot.exists():
        outputs.append(str(ts_plot))

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
