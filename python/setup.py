from __future__ import annotations

import platform
import sys
from datetime import datetime
from pathlib import Path

from config import detect_project_root


def setup_project() -> dict[str, str]:
    root = detect_project_root()
    logs_dir = root / "outputs" / "_run_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    required = [
        "pandas",
        "geopandas",
        "rasterio",
        "openpyxl",
        "scipy",
        "sklearn",
        "networkx",
        "skbio",
    ]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except Exception:
            missing.append(pkg)

    if missing:
        raise RuntimeError(
            f"Missing required packages: {', '.join(missing)}. Install them in .venv and rerun setup."
        )

    info_path = logs_dir / "session_info.txt"
    lines = [
        f"Setup timestamp: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"Python version: {sys.version}",
        f"Platform: {platform.platform()}",
        f"Project root: {root}",
    ]
    info_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Setup complete. Session log written to: {info_path}")
    return {"root": str(root), "session_info": str(info_path)}


if __name__ == "__main__":
    setup_project()
