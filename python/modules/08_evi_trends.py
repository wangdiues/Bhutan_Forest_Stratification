from __future__ import annotations

import time
import json

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for thread-safe parallel execution
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kendalltau, theilslopes

try:
    from utils import check_file, ensure_dirs, normalize_name, save_plot
except ImportError:
    from python.utils import check_file, ensure_dirs, normalize_name, save_plot


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


def _save_trend_map(map_df: pd.DataFrame, out_map, palette: dict) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    for cls, sub in map_df.groupby("trend_class", dropna=False):
        ax.scatter(sub["longitude"], sub["latitude"], color=palette.get(str(cls), "grey"), alpha=0.8, label=str(cls))
    ax.set_title("EVI trend classes")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend()
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

            # Replicate country trend to plot points so map outputs remain available for workflow continuity.
            if pts_df is not None and not pts_df.empty:
                rep = pts_df[["plot_id", "longitude", "latitude"]].copy()
                rep["theil_sen_slope"] = national["theil_sen_slope"]
                rep["mk_p_value"] = national["mk_p_value"]
                rep["n_obs"] = national["n_obs"]
                rep["trend_class"] = national["trend_class"]
                rep["trend_unit"] = "country_replicated_to_plots"
                rep.to_csv(out_table, index=False)
                _save_trend_map(rep, out_map, config["colors"]["trend"])
                warnings.append("Replicated country-level EVI trend to plot points for map generation.")
    else:
        raise RuntimeError("EVI CSV does not contain required fields for trend analysis (plot_id+time or date).")

    outputs = [str(out_table)]
    if out_map.with_suffix(".png").exists():
        outputs.append(str(out_map))

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
