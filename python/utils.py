from __future__ import annotations

import importlib
import json
import logging
import os
import pickle
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_packages(packages: Iterable[str]) -> None:
    missing = []
    for pkg in packages:
        try:
            importlib.import_module(pkg)
        except Exception:
            missing.append(pkg)
    if missing:
        raise RuntimeError(f"Missing Python packages: {', '.join(missing)}")


def ensure_dirs(module_name: str, config: dict[str, Any]) -> Path:
    root = config["output"]["module_dirs"].get(module_name)
    if root is None:
        raise RuntimeError(f"Unknown module name for directory creation: {module_name}")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for sub in config["output"]["module_subdirs"].get(module_name, []):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def check_file(path: str | Path, desc: str, required: bool = True) -> bool:
    p = Path(path)
    ok = p.exists()
    if required and not ok:
        raise RuntimeError(f"{desc} not found: {p}")
    return ok


def check_columns(df: pd.DataFrame, required: list[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise RuntimeError(f"Missing required columns: {', '.join(missing)}")


def setup_logging(config: dict, level: str = "INFO") -> logging.Logger:
    """
    Initialize structured logging with file and console handlers.

    Creates a timestamped log file in outputs/_run_logs/ and configures
    both file (DEBUG+) and console (INFO+) output.

    Args:
        config: Project configuration dict with paths
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured root logger for the pipeline
    """
    log_dir = Path(config["paths"]["logs"]["run_logs_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    # Root logger
    logger = logging.getLogger("bhutan_pipeline")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # File handler (DEBUG and above)
    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(file_formatter)

    # Console handler (INFO and above)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(console_formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"Log file: {log_file}")
    return logger


def get_module_logger(module_name: str) -> logging.Logger:
    """
    Get a child logger for a specific module.

    Args:
        module_name: Name of the module (e.g., "00_data_inspection")

    Returns:
        Child logger instance
    """
    return logging.getLogger(f"bhutan_pipeline.{module_name}")


def log_section(text: str) -> None:
    """Legacy logging function - prints section header."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {text.upper()}")


def log_step(text: str) -> None:
    """Legacy logging function - prints step message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] - {text}")


def log_done(text: str) -> None:
    """Legacy logging function - prints completion message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] DONE: {text}")


def save_plot(fig: plt.Figure, path: str | Path, dpi: int = 500) -> list[str]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    png_path = target.with_suffix(".png")
    pdf_path = target.with_suffix(".pdf")
    fig.savefig(png_path, dpi=dpi, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    return [str(png_path), str(pdf_path)]


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def standardize_columns(df: pd.DataFrame, mapping_candidates: dict[str, list[str]]) -> pd.DataFrame:
    df = df.copy()
    normalized_cols = {normalize_name(c): c for c in df.columns}

    for canonical, candidates in mapping_candidates.items():
        if canonical in df.columns:
            continue
        for candidate in candidates:
            hit = normalized_cols.get(normalize_name(candidate))
            if hit is not None:
                df = df.rename(columns={hit: canonical})
                break

    if "forest_type" in df.columns:
        df["forest_type"] = df["forest_type"].astype(str)
    if "stratum" in df.columns:
        df["stratum"] = df["stratum"].astype(str)

    return df


def clean_sp_names(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)


def make_species_matrix(veg_long: pd.DataFrame) -> pd.DataFrame:
    check_columns(veg_long, ["plot_id", "species_name"])
    data = veg_long.copy()
    data["plot_id"] = data["plot_id"].astype(str)
    data["species_name"] = clean_sp_names(data["species_name"])
    if "abundance" in data.columns:
        abund = pd.to_numeric(data["abundance"], errors="coerce").fillna(1.0)
        data["_abund"] = abund
        mat = data.pivot_table(index="plot_id", columns="species_name", values="_abund", aggfunc="sum", fill_value=0)
    else:
        data["_abund"] = 1.0
        mat = data.pivot_table(index="plot_id", columns="species_name", values="_abund", aggfunc="sum", fill_value=0)
    return mat.astype(float)


def as_plain_matrix(x: Any) -> np.ndarray:
    if isinstance(x, pd.DataFrame):
        return x.to_numpy(dtype=float)
    return np.asarray(x, dtype=float)


def read_if_exists(path: str | Path, reader):
    p = Path(path)
    if not p.exists():
        return None
    return reader(p)


def safe_z(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    s = x.std(skipna=True)
    if pd.isna(s) or s == 0:
        return pd.Series([0.0] * len(x), index=x.index)
    return (x - x.mean(skipna=True)) / s


def save_pickle(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{p.stem}_", suffix=".tmp", dir=p.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with tmp_path.open("wb") as f:
            pickle.dump(obj, f)
        for _ in range(3):
            try:
                os.replace(tmp_path, p)
                break
            except PermissionError:
                time.sleep(0.05)
        else:
            with p.open("wb") as f:
                pickle.dump(obj, f)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except PermissionError:
                pass


def load_pickle(path: str | Path) -> Any:
    with Path(path).open("rb") as f:
        return pickle.load(f)


def write_json(path: str | Path, payload: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{p.stem}_", suffix=".tmp", dir=p.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        for _ in range(3):
            try:
                os.replace(tmp_path, p)
                break
            except PermissionError:
                time.sleep(0.05)
        else:
            with p.open("w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except PermissionError:
                pass
