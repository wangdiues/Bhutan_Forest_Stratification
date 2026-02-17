from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from python.utils import ensure_dirs


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_dir = ensure_dirs("11_reporting", config)

    alpha_path = config["output"]["module_dirs"]["03_alpha_diversity"] / "tables" / "alpha_diversity_summary.csv"
    sci_path = config["output"]["module_dirs"]["09_sci_index"] / "tables" / "stratification_complexity_index.csv"
    ind_path = config["output"]["module_dirs"]["06_indicator_species"] / "tables" / "indicator_species_by_forest_type.csv"

    outputs = []
    warnings = []

    if alpha_path.exists() and sci_path.exists():
        alpha = pd.read_csv(alpha_path)
        sci = pd.read_csv(sci_path)
        if {"plot_id", "richness", "shannon"}.issubset(alpha.columns) and "sci_index" in sci.columns:
            summary_tbl = (
                alpha[["plot_id", "forest_type", "richness", "shannon"]]
                .merge(sci[["plot_id", "sci_index"]], on="plot_id", how="left")
                .groupby("forest_type", dropna=False)
                .agg(
                    n_plots=("plot_id", "size"),
                    mean_richness=("richness", "mean"),
                    mean_shannon=("shannon", "mean"),
                    mean_sci=("sci_index", "mean"),
                )
                .reset_index()
            )
            f_summary = out_dir / "summary_by_forest_type.csv"
            summary_tbl.to_csv(f_summary, index=False)
            outputs.append(str(f_summary))
        else:
            warnings.append("Skipping summary_by_forest_type: required columns missing in alpha or SCI tables.")
    else:
        warnings.append("Skipping summary_by_forest_type: alpha or SCI table not found.")

    if ind_path.exists():
        ind = pd.read_csv(ind_path)
        f_ind = out_dir / "summary_top_20_indicator_species.csv"
        ind.head(20).to_csv(f_ind, index=False)
        outputs.append(str(f_ind))
    else:
        warnings.append("Skipping top indicator species summary: indicator table not found.")

    key_tables = []
    key_figures = []
    candidate_tables = [
        out_dir / "summary_by_forest_type.csv",
        out_dir / "summary_top_20_indicator_species.csv",
    ]
    candidate_figures = [
        config["output"]["module_dirs"]["10_spatial_mapping"] / "map_species_richness.png",
        config["output"]["module_dirs"]["10_spatial_mapping"] / "map_sci_index.png",
        config["output"]["module_dirs"]["10_spatial_mapping"] / "map_nmds1_scores.png",
        config["output"]["module_dirs"]["10_spatial_mapping"] / "map_evi_trends.png",
    ]
    for p in candidate_tables:
        if Path(p).exists():
            key_tables.append(f"- `{Path(p).as_posix()}`")
    for p in candidate_figures:
        if Path(p).exists():
            key_figures.append(f"- `{Path(p).as_posix()}`")

    md_path = out_dir / "pipeline_report.md"
    md_lines = [
        "# Bhutan Forest Stratification Pipeline Report",
        "",
        "## Run Context",
        "",
        "This report is generated from pipeline outputs under `outputs/`.",
        "",
        "## Key Tables",
        "",
        *(key_tables or ["- No key tables were generated in this run."]),
        "",
        "## Key Figures",
        "",
        *(key_figures or ["- No key figures were generated in this run."]),
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    outputs.append(str(md_path))

    manifest = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "files": outputs,
    }
    manifest_path = out_dir / "report_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    outputs.append(str(manifest_path))

    return {
        "status": "success",
        "outputs": outputs,
        "warnings": warnings,
        "runtime_sec": time.time() - t0,
    }
