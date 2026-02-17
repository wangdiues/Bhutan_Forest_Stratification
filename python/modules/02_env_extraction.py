from __future__ import annotations

import time

import numpy as np
import pandas as pd
from rasterio.warp import transform
import re

try:
    from utils import check_columns, check_file, ensure_dirs, normalize_name, save_pickle
except ImportError:
    from python.utils import check_columns, check_file, ensure_dirs, normalize_name, save_pickle


def _to_raster_crs_coords(lon: np.ndarray, lat: np.ndarray, raster_crs) -> tuple[np.ndarray, np.ndarray]:
    if raster_crs is None:
        return lon, lat
    xs, ys = transform("EPSG:4326", raster_crs, lon.tolist(), lat.tolist())
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)


def _sample_raster(points_df: pd.DataFrame, path, lon_col="longitude", lat_col="latitude") -> np.ndarray:
    import rasterio

    if not path.exists():
        return np.full(len(points_df), np.nan)

    lon = pd.to_numeric(points_df[lon_col], errors="coerce").to_numpy(dtype=float)
    lat = pd.to_numeric(points_df[lat_col], errors="coerce").to_numpy(dtype=float)
    with rasterio.open(path) as src:
        xs, ys = _to_raster_crs_coords(lon, lat, src.crs)
        coords = list(zip(xs, ys))
        vals = [v[0] if len(v) > 0 else np.nan for v in src.sample(coords)]
    return np.asarray(vals, dtype=float)


def _sample_dem_slope_aspect(points_df: pd.DataFrame, dem_path) -> tuple[np.ndarray, np.ndarray]:
    import rasterio
    from rasterio.windows import Window

    n = len(points_df)
    slope = np.full(n, np.nan, dtype=float)
    aspect = np.full(n, np.nan, dtype=float)
    if not dem_path.exists():
        return slope, aspect

    lon = pd.to_numeric(points_df["longitude"], errors="coerce").to_numpy(dtype=float)
    lat = pd.to_numeric(points_df["latitude"], errors="coerce").to_numpy(dtype=float)

    with rasterio.open(dem_path) as src:
        xs, ys = _to_raster_crs_coords(lon, lat, src.crs)
        xres, yres = src.res

        for i, (x, y) in enumerate(zip(xs, ys)):
            try:
                row, col = src.index(x, y)
                if row < 1 or col < 1 or row >= src.height - 1 or col >= src.width - 1:
                    continue
                win = Window(col_off=col - 1, row_off=row - 1, width=3, height=3)
                z = src.read(1, window=win, masked=True)
                if np.ma.is_masked(z) and np.any(z.mask):
                    continue
                z = np.asarray(z, dtype=float)

                dzdx = ((z[0, 2] + 2 * z[1, 2] + z[2, 2]) - (z[0, 0] + 2 * z[1, 0] + z[2, 0])) / (8 * xres)
                dzdy = ((z[2, 0] + 2 * z[2, 1] + z[2, 2]) - (z[0, 0] + 2 * z[0, 1] + z[0, 2])) / (8 * yres)
                slope[i] = float(np.degrees(np.arctan(np.sqrt(dzdx**2 + dzdy**2))))
                asp = np.degrees(np.arctan2(dzdy, -dzdx))
                aspect[i] = float((asp + 360.0) % 360.0)
            except Exception:
                continue

    return slope, aspect


def _discover_bioclim_rasters(climate_dir) -> dict[str, object]:
    rasters: dict[str, object] = {}
    if not climate_dir.exists():
        return rasters
    for tif in sorted(climate_dir.glob("*.tif")):
        m = re.search(r"bio(\d+)", tif.name.lower())
        if m:
            idx = int(m.group(1))
            rasters[f"bio{idx}"] = tif
    return rasters


def module_run(config: dict) -> dict:
    t0 = time.time()
    ensure_dirs("02_env_extraction", config)
    warnings = []

    pts = None
    gpkg_path = config["paths"]["canonical"]["plot_points_gpkg"]
    if gpkg_path.exists() and gpkg_path.stat().st_size > 0:
        try:
            import geopandas as gpd

            pts = gpd.read_file(gpkg_path).to_crs(epsg=config["params"]["crs_epsg"])
            if pts.empty:
                warnings.append("plot_points.gpkg is empty; falling back to coordinate CSV.")
                pts = None
        except Exception as exc:
            warnings.append(f"Could not read plot_points.gpkg: {exc}")
    elif gpkg_path.exists():
        warnings.append("plot_points.gpkg exists but is empty; falling back to coordinate CSV.")

    if pts is None:
        csv_path = config["paths"]["compatibility"]["plot_coordinates_cleaned_csv"]
        if not csv_path.exists():
            raise RuntimeError("Required input missing: plot points gpkg/csv. Run module 01 first.")
        coords = pd.read_csv(csv_path)
        check_columns(coords, ["plot_id", "longitude", "latitude"])
        pts = coords.copy()

    if "geometry" in getattr(pts, "columns", []):
        env = pts.drop(columns="geometry", errors="ignore").copy()
        env["longitude"] = pts.geometry.x
        env["latitude"] = pts.geometry.y
    else:
        env = pts.copy()

    env["longitude"] = pd.to_numeric(env["longitude"], errors="coerce")
    env["latitude"] = pd.to_numeric(env["latitude"], errors="coerce")
    env = env.dropna(subset=["longitude", "latitude"]).copy()
    if env.empty:
        raise RuntimeError("No valid coordinates available for environmental extraction.")

    n = len(env)
    for c in ["forest_type", "forest_raster_value", "dzongkhag", "geog_name", "area_ha", "ForTyp"]:
        if c not in env.columns:
            env[c] = np.nan

    ftm_path = config["paths"]["inputs"]["forest_type_map"]
    if check_file(ftm_path, "Forest type map", required=False):
        try:
            import geopandas as gpd

            if "geometry" in getattr(pts, "columns", []):
                ftm = gpd.read_file(ftm_path)
                pts_ftm = pts.to_crs(ftm.crs) if pts.crs != ftm.crs else pts
                joined = gpd.sjoin_nearest(pts_ftm, ftm, how="left")
                j = joined.drop(columns="geometry", errors="ignore")

                def get_col(df, candidates):
                    for cand in candidates:
                        hits = [c for c in df.columns if normalize_name(c) == normalize_name(cand)]
                        if hits:
                            return df[hits[0]]
                    return pd.Series([np.nan] * len(df))

                env["forest_type"] = get_col(j, ["forest_type", "ForTyp", "for_typ"]).astype(str)
                env["ForTyp"] = env["forest_type"]
                env["forest_raster_value"] = pd.to_numeric(get_col(j, ["RasterValu", "raster_value", "class"]), errors="coerce")
                env["dzongkhag"] = get_col(j, ["DzgName", "dzongkhag"]).astype(str)
                env["geog_name"] = get_col(j, ["GeogName", "geog_name"]).astype(str)
                env["area_ha"] = pd.to_numeric(get_col(j, ["Area_ha", "area_ha"]), errors="coerce")
        except Exception as exc:
            warnings.append(f"Forest type join failed: {exc}")
    else:
        warnings.append(f"Missing forest type map: {ftm_path}")

    soil_vector = config["paths"]["inputs"]["soil_map_vector"]
    if check_file(soil_vector, "Soil map vector", required=False):
        try:
            import geopandas as gpd

            if "geometry" in getattr(pts, "columns", []):
                pts_soil = pts.copy()
            else:
                pts_soil = gpd.GeoDataFrame(
                    env[["plot_id", "longitude", "latitude"]].copy(),
                    geometry=gpd.points_from_xy(env["longitude"], env["latitude"]),
                    crs=f"EPSG:{config['params']['crs_epsg']}",
                )

            soil = gpd.read_file(soil_vector)
            pts_s = pts_soil.to_crs(soil.crs) if pts_soil.crs != soil.crs else pts_soil
            try:
                joined_soil = gpd.sjoin(pts_s, soil, how="left", predicate="within")
            except Exception:
                joined_soil = gpd.sjoin_nearest(pts_s, soil, how="left")
            js = joined_soil.drop(columns="geometry", errors="ignore")

            soil_col = next(
                (c for c in js.columns if normalize_name(c) in {"soiltype", "soil_type", "gridcode"}),
                None,
            )
            if soil_col is not None:
                env["soil_type"] = js[soil_col].astype(str)
        except Exception as exc:
            warnings.append(f"Soil type vector join failed: {exc}")

    env["elevation"] = _sample_raster(env, config["paths"]["inputs"]["dem"])

    climate_dir = config["paths"]["inputs"]["climate_dir"]
    bio_rasters = _discover_bioclim_rasters(climate_dir) if config["params"].get("extract_all_bioclim", True) else {}
    if not bio_rasters:
        # Compatibility fallback to configured primary rasters.
        bio_rasters = {
            "bio1": config["paths"]["inputs"]["climate_bio1"],
            "bio12": config["paths"]["inputs"]["climate_bio12"],
        }

    for bio_name, bio_path in bio_rasters.items():
        env[bio_name] = _sample_raster(env, bio_path)

    # Maintain canonical compatibility names.
    if "bio1" in env.columns:
        bio1_raw = pd.to_numeric(env["bio1"], errors="coerce")
        bio1_adj = bio1_raw.copy()
        if config["params"].get("bio1_auto_scale", True):
            med_abs = float(np.nanmedian(np.abs(bio1_raw.to_numpy(dtype=float)))) if bio1_raw.notna().any() else np.nan
            if pd.notna(med_abs) and med_abs > float(config["params"].get("bio1_scale_threshold_abs_c", 80.0)):
                bio1_adj = bio1_raw / 10.0
                warnings.append("BIO1 appears scaled (|median| > threshold); converted by dividing by 10.")
        if bio1_adj.notna().any():
            if float(np.nanmax(np.abs(bio1_adj.to_numpy(dtype=float)))) > 60:
                warnings.append("BIO1 temperature values still look extreme after scaling check; verify source units.")
        env["bio1_temperature"] = bio1_adj
    else:
        env["bio1_temperature"] = np.nan
        warnings.append("BIO1 raster not found; bio1_temperature set to NA.")

    if "bio12" in env.columns:
        bio12 = pd.to_numeric(env["bio12"], errors="coerce")
        if bio12.notna().any() and float(np.nanmin(bio12.to_numpy(dtype=float))) < 0:
            warnings.append("BIO12 precipitation contains negative values; verify source raster.")
        env["bio12_ppt"] = bio12
    else:
        env["bio12_ppt"] = np.nan
        warnings.append("BIO12 raster not found; bio12_ppt set to NA.")

    if "soil_type" not in env.columns or env["soil_type"].isna().all():
        env["soil_type"] = _sample_raster(env, config["paths"]["inputs"]["soil_map_raster"])
    slope, aspect = _sample_dem_slope_aspect(env, config["paths"]["inputs"]["dem"])
    env["slope"] = slope
    env["aspect"] = aspect

    evi_path = config["paths"]["inputs"]["evi_csv"]
    env["evi_mean_country"] = np.nan
    env["evi_median_country"] = np.nan
    env["evi_cv_country"] = np.nan
    if evi_path.exists():
        evi = pd.read_csv(evi_path)
        evi_col = next((c for c in evi.columns if normalize_name(c) == "evi"), None)
        if evi_col:
            vv = pd.to_numeric(evi[evi_col], errors="coerce")
            mean_v = float(vv.mean(skipna=True))
            env["evi_mean_country"] = mean_v
            env["evi_median_country"] = float(vv.median(skipna=True))
            env["evi_cv_country"] = float((vv.std(skipna=True) / mean_v) * 100) if mean_v else np.nan
        else:
            warnings.append("EVI CSV found but EVI column was not detected.")
    else:
        warnings.append(f"Missing EVI CSV: {evi_path}")

    env["lat_elevation_proxy"] = (env["latitude"] - env["latitude"].min()) * 1000
    env["dist_from_center"] = np.sqrt((env["latitude"] - 27.5) ** 2 + (env["longitude"] - 90.5) ** 2)

    env.to_csv(config["paths"]["canonical"]["env_master_csv"], index=False)
    save_pickle(config["paths"]["canonical"]["env_master_rds"], env)
    env.to_csv(config["paths"]["compatibility"]["master_environmental_data_csv"], index=False)
    env.to_csv(config["paths"]["compatibility"]["master_environmental_data_with_ftm_csv"], index=False)

    return {
        "status": "success",
        "outputs": [
            str(config["paths"]["canonical"]["env_master_csv"]),
            str(config["paths"]["canonical"]["env_master_rds"]),
            str(config["paths"]["compatibility"]["master_environmental_data_csv"]),
            str(config["paths"]["compatibility"]["master_environmental_data_with_ftm_csv"]),
        ],
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
