from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd

from python.utils import (
    check_columns,
    check_file,
    clean_sp_names,
    ensure_dirs,
    flag_taxonomic_duplicates,
    make_species_matrix,
    save_pickle,
    standardize_columns,
)


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_dir = ensure_dirs("01_data_cleaning", config)
    in_xlsx = config["paths"]["inputs"]["vegetation_xlsx"]
    check_file(in_xlsx, "Vegetation workbook", required=True)

    wanted = ["Trees", "Shrubs", "Herbs", "Regeneration"]
    xls = pd.ExcelFile(in_xlsx)
    available = xls.sheet_names
    use_sheets = [s for s in wanted if s in available]
    if not use_sheets:
        raise RuntimeError("No expected sheets found in vegetation workbook. Expected one of: Trees, Shrubs, Herbs, Regeneration.")

    veg_raw = pd.concat([pd.read_excel(in_xlsx, sheet_name=s).assign(stratum=s) for s in use_sheets], ignore_index=True)

    veg = standardize_columns(veg_raw, config["columns"]["mappings"])
    for c in veg.select_dtypes(include=["object"]).columns:
        veg[c] = veg[c].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    if "plot_id" not in veg.columns:
        raise RuntimeError("plot_id column missing after standardization")
    if "species_name" not in veg.columns:
        raise RuntimeError("species_name column missing after standardization")

    veg["plot_id"] = veg["plot_id"].astype(str)
    veg["species_name"] = clean_sp_names(veg["species_name"])
    veg["stratum"] = veg.get("stratum", pd.Series(dtype=str)).astype(str)

    if "longitude" not in veg.columns:
        veg["longitude"] = np.nan
    if "latitude" not in veg.columns:
        veg["latitude"] = np.nan

    veg["longitude"] = pd.to_numeric(veg["longitude"], errors="coerce")
    veg["latitude"] = pd.to_numeric(veg["latitude"], errors="coerce")

    check_columns(veg, ["plot_id", "species_name", "stratum"])
    veg = veg[(veg["plot_id"].notna()) & (veg["plot_id"] != "") & (veg["species_name"].notna()) & (veg["species_name"] != "")]

    veg.to_csv(config["paths"]["canonical"]["veg_long_csv"], index=False)
    save_pickle(config["paths"]["canonical"]["veg_long_rds"], veg)
    veg.to_csv(config["paths"]["compatibility"]["vegetation_data_cleaned_csv"], index=False)

    sp_mat = make_species_matrix(veg)
    save_pickle(config["paths"]["canonical"]["sp_mat_rds"], sp_mat)

    # ── Taxonomic duplicate-candidate report ──────────────────────────────────
    # Flag pairs of species names within the same genus that differ by ≤ 2
    # characters (Levenshtein distance on the epithet).  These are potential
    # typos or orthographic variants that inflate the species count artificially.
    # The report requires MANUAL REVIEW before the final manuscript run.
    out_taxa_dir = ensure_dirs("01_data_cleaning", config)
    occ_counts   = (sp_mat > 0).sum(axis=0)  # n plots per species
    species_in_data = sp_mat.columns.astype(str).tolist()
    dup_df = flag_taxonomic_duplicates(species_in_data)
    if not dup_df.empty:
        dup_df["n_plots_a"] = dup_df["name_a"].map(
            occ_counts.to_dict()).fillna(0).astype(int)
        dup_df["n_plots_b"] = dup_df["name_b"].map(
            occ_counts.to_dict()).fillna(0).astype(int)
        dup_df = dup_df.sort_values(["genus", "edit_distance"])
    f_taxa_dup = out_taxa_dir / "taxonomic_duplicate_candidates.csv"
    dup_df.to_csv(f_taxa_dup, index=False)
    n_dup_pairs = len(dup_df)

    plot_df = (
        veg[["plot_id", "longitude", "latitude"]]
        .drop_duplicates()
        .dropna(subset=["longitude", "latitude"])
    )
    plot_df = plot_df[
        plot_df["latitude"].between(-90, 90) & plot_df["longitude"].between(-180, 180)
    ]

    warnings = []
    if len(plot_df) > 0:
        try:
            import geopandas as gpd

            gpkg_path = config["paths"]["canonical"]["plot_points_gpkg"]
            tmp_gpkg = gpkg_path.with_name(f"{gpkg_path.stem}_{int(time.time())}.gpkg")
            gdf = gpd.GeoDataFrame(
                plot_df.copy(),
                geometry=gpd.points_from_xy(plot_df["longitude"], plot_df["latitude"]),
                crs=f"EPSG:{config['params']['crs_epsg']}",
            )
            gdf.to_file(tmp_gpkg, driver="GPKG")

            # Validate temp gpkg before replacing the canonical file.
            gdf_check = gpd.read_file(tmp_gpkg)
            if gdf_check.empty:
                raise RuntimeError("Temporary plot_points.gpkg validation failed (no features).")

            os.replace(tmp_gpkg, gpkg_path)
            tmp_journal = tmp_gpkg.with_name(tmp_gpkg.name + "-journal")
            if tmp_journal.exists():
                tmp_journal.unlink(missing_ok=True)
        except Exception as exc:
            warnings.append(f"Failed to write plot_points.gpkg: {exc}")
            gpkg_path = config["paths"]["canonical"]["plot_points_gpkg"]
            if gpkg_path.exists() and gpkg_path.stat().st_size == 0:
                gpkg_path.unlink(missing_ok=True)
    else:
        warnings.append("No valid coordinates found after cleaning; plot_points.gpkg was not created.")

    plot_df.to_csv(config["paths"]["compatibility"]["plot_coordinates_cleaned_csv"], index=False)

    outputs = [
        str(config["paths"]["canonical"]["veg_long_csv"]),
        str(config["paths"]["canonical"]["veg_long_rds"]),
        str(config["paths"]["canonical"]["sp_mat_rds"]),
        str(config["paths"]["compatibility"]["vegetation_data_cleaned_csv"]),
        str(config["paths"]["compatibility"]["plot_coordinates_cleaned_csv"]),
        str(f_taxa_dup),
    ]
    if config["paths"]["canonical"]["plot_points_gpkg"].exists():
        outputs.append(str(config["paths"]["canonical"]["plot_points_gpkg"]))

    missing_sheets = [s for s in wanted if s not in available]
    if missing_sheets:
        warnings.append(f"Missing expected sheets: {', '.join(missing_sheets)}")
    if n_dup_pairs > 0:
        warnings.append(
            f"Taxonomic QC: {n_dup_pairs} near-duplicate species name pair(s) detected "
            f"(Levenshtein ≤ 2 within genus). See taxonomic_duplicate_candidates.csv "
            f"for manual review BEFORE final manuscript run."
        )

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
