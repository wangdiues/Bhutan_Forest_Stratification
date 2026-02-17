from __future__ import annotations

import time

import numpy as np
import pandas as pd

from python.utils import check_file, ensure_dirs


def module_run(config: dict) -> dict:
    t0 = time.time()
    out_dir = ensure_dirs("02b_qc_after_env_extraction", config)
    check_file(config["paths"]["canonical"]["env_master_csv"], "Canonical environmental table", required=True)

    env = pd.read_csv(config["paths"]["canonical"]["env_master_csv"])

    num_cols = [c for c in env.columns if pd.api.types.is_numeric_dtype(env[c])]
    predictors = [c for c in num_cols if c not in {"longitude", "latitude"}]

    na_rates = pd.DataFrame({"predictor": predictors, "na_rate": [env[p].isna().mean() for p in predictors]})

    outlier_rows = []
    for p in predictors:
        x = pd.to_numeric(env[p], errors="coerce")
        q1, q3 = x.quantile([0.25, 0.75])
        iqr = q3 - q1
        lo = q1 - config["params"]["outlier_iqr_multiplier"] * iqr
        hi = q3 + config["params"]["outlier_iqr_multiplier"] * iqr
        n_out = int(((x < lo) | (x > hi)).sum())
        outlier_rows.append({"predictor": p, "n_outliers": n_out, "lower_bound": lo, "upper_bound": hi})
    outlier_summary = pd.DataFrame(outlier_rows)

    corr_pairs = pd.DataFrame(columns=["var1", "var2", "correlation"])
    if len(predictors) >= 2:
        cm = env[predictors].corr(method="pearson", min_periods=2)
        rows = []
        for i, r in enumerate(cm.index):
            for j, c in enumerate(cm.columns):
                if j <= i:
                    continue
                v = cm.iloc[i, j]
                if pd.notna(v) and abs(v) >= config["params"]["correlation_flag_threshold"]:
                    rows.append({"var1": r, "var2": c, "correlation": v})
        corr_pairs = pd.DataFrame(rows)

    f_na = out_dir / "qc_after_env_na_rates.csv"
    f_out = out_dir / "qc_after_env_outliers.csv"
    f_cor = out_dir / "qc_after_env_collinearity.csv"
    f_txt = out_dir / "qc_after_env_summary.txt"

    na_rates.to_csv(f_na, index=False)
    outlier_summary.to_csv(f_out, index=False)
    corr_pairs.to_csv(f_cor, index=False)

    f_txt.write_text(
        "\n".join(
            [
                "QC after environmental extraction",
                f"Rows in env_master: {len(env)}",
                f"Predictors checked: {len(predictors)}",
                f"High-correlation pairs (|r| >= {config['params']['correlation_flag_threshold']:.2f}): {len(corr_pairs)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "status": "success",
        "outputs": [str(f_na), str(f_out), str(f_cor), str(f_txt)],
        "warnings": [],
        "runtime_sec": time.time() - t0,
    }
