from __future__ import annotations

import time

import pandas as pd

try:
    from utils import check_columns, ensure_dirs
except ImportError:
    from python.utils import check_columns, ensure_dirs


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_dir = ensure_dirs("01b_qc_after_cleaning", config)

    veg = pd.read_csv(config["paths"]["canonical"]["veg_long_csv"])
    check_columns(veg, ["plot_id", "species_name", "stratum"])

    dup_tbl = (
        veg.groupby(["plot_id", "species_name", "stratum"], dropna=False)
        .size()
        .reset_index(name="n")
    )
    dup_tbl = dup_tbl[dup_tbl["n"] > 1].sort_values("n", ascending=False)

    missing_tbl = pd.DataFrame({
        "column": veg.columns,
        "missing_n": [int(veg[c].isna().sum() + (veg[c].astype(str) == "").sum()) for c in veg.columns],
        "total_n": len(veg),
    })
    missing_tbl["missing_pct"] = (100 * missing_tbl["missing_n"] / max(len(veg), 1)).round(2)

    sp_count = veg[["plot_id", "species_name"]].drop_duplicates().groupby("plot_id").size().reset_index(name="species_richness")

    bbox = config["params"]["bhutan_bbox"]
    coord_tbl = pd.DataFrame()

    gpkg = config["paths"]["canonical"]["plot_points_gpkg"]
    coords_csv = config["paths"]["compatibility"]["plot_coordinates_cleaned_csv"]
    if gpkg.exists():
        try:
            import geopandas as gpd

            pts = gpd.read_file(gpkg).to_crs(epsg=config["params"]["crs_epsg"])
            coord_tbl = pts.drop(columns="geometry", errors="ignore")
            coord_tbl["inside_bbox"] = (
                coord_tbl["longitude"].between(bbox["lon_min"], bbox["lon_max"]) &
                coord_tbl["latitude"].between(bbox["lat_min"], bbox["lat_max"])
            )
        except Exception:
            coord_tbl = pd.DataFrame()

    if coord_tbl.empty and coords_csv.exists():
        coords = pd.read_csv(coords_csv)
        if {"plot_id", "longitude", "latitude"}.issubset(coords.columns):
            coord_tbl = coords.copy()
            coord_tbl["inside_bbox"] = (
                coord_tbl["longitude"].between(bbox["lon_min"], bbox["lon_max"]) &
                coord_tbl["latitude"].between(bbox["lat_min"], bbox["lat_max"])
            )

    f_dup = out_dir / "qc_after_cleaning_duplicates.csv"
    f_missing = out_dir / "qc_after_cleaning_missingness.csv"
    f_sp = out_dir / "qc_after_cleaning_species_count_by_plot.csv"
    f_coord = out_dir / "qc_after_cleaning_coordinate_checks.csv"
    f_txt = out_dir / "qc_after_cleaning_summary.txt"

    dup_tbl.to_csv(f_dup, index=False)
    missing_tbl.to_csv(f_missing, index=False)
    sp_count.to_csv(f_sp, index=False)
    coord_tbl.to_csv(f_coord, index=False)

    lines = [
        "QC after cleaning",
        f"Rows in veg_long: {len(veg)}",
        f"Duplicate plot-species-stratum rows: {len(dup_tbl)}",
        f"Plots in species summary: {len(sp_count)}",
        f"Coordinate rows checked: {len(coord_tbl)}",
    ]
    if len(coord_tbl) > 0:
        lines.append(f"Coordinates outside Bhutan bbox: {int((~coord_tbl['inside_bbox']).sum())}")
    else:
        lines.append("Coordinates outside Bhutan bbox: NA")
    f_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "status": "success",
        "outputs": [str(f_dup), str(f_missing), str(f_sp), str(f_coord), str(f_txt)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
