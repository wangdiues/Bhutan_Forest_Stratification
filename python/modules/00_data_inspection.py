from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from python.utils import ensure_dirs


def module_run(config: dict) -> dict:
    t0 = time.time()
    output_dir = ensure_dirs("00_data_inspection", config)

    inventory_csv = output_dir / "data_inventory.csv"
    inventory_txt = output_dir / "data_inventory.txt"

    targets = {}
    for section in ["inputs", "canonical", "compatibility"]:
        for k, v in config["paths"][section].items():
            targets[k] = Path(v)

    rows = []
    for key, path in targets.items():
        exists = path.exists()
        ext = path.suffix.lower().lstrip(".")
        if not exists:
            kind = "missing"
        elif ext in {"shp", "gpkg"}:
            kind = "vector"
        elif ext in {"tif", "tiff", "nc"}:
            kind = "raster"
        elif ext in {"csv", "txt", "xlsx", "rds", "json"}:
            kind = "tabular_or_serialized"
        else:
            kind = "other"
        stat = path.stat() if exists else None
        rows.append(
            {
                "key": key,
                "path": str(path),
                "exists": exists,
                "kind": kind,
                "size_bytes": stat.st_size if stat else None,
                "modified_time": stat.st_mtime if stat else None,
            }
        )

    inventory = pd.DataFrame(rows)
    inventory.to_csv(inventory_csv, index=False)

    missing = inventory[~inventory["exists"]]
    lines = [
        "Bhutan Forest Stratification - Data Inventory",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        f"Total targets: {len(inventory)}",
        f"Available: {int(inventory['exists'].sum())}",
        f"Missing: {int((~inventory['exists']).sum())}",
        "",
        "Missing files:",
    ]
    if len(missing) > 0:
        lines.extend([f"- {r.key} -> {r.path}" for r in missing.itertuples()])
    else:
        lines.append("- none")
    inventory_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "status": "success",
        "outputs": [str(inventory_csv), str(inventory_txt)],
        "warnings": ["Some expected inputs/intermediates are missing. See data_inventory.csv."] if len(missing) > 0 else [],
        "runtime_sec": time.time() - t0,
    }
