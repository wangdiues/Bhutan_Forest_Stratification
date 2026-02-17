# Bhutan Forest Stratification and Vertical Zonation Pipeline Context

## Overview
This repository contains a production-oriented Python implementation of the Bhutan forest stratification analysis workflow under `python/`, with legacy R scripts preserved under `scripts/` for reference.

The Python implementation enforces:
- deterministic module orchestration (`python/run_pipeline.py`)
- centralized configuration (`python/config.py`)
- shared utility functions (`python/utils.py`)
- output validation layer (`python/validation.py`)
- module-level contracts (`module_run(config)`)
- reproducibility outputs (`.pkl` plus human-readable `.csv`)
- explicit failure behavior for missing required inputs (no automatic downloads)
- structured logging with file and console outputs

## Directory Structure
- `python/setup.py`: environment validation and run log setup
- `python/config.py`: root detection, paths, parameters, canonical column mappings
- `python/utils.py`: shared utilities and logging helpers
- `python/validation.py`: output validation layer
- `python/performance.py`: resource monitoring and progress utilities
- `python/run_pipeline.py`: module registry, dependency handling, parallel execution, manifest writing
- `python/modules/*.py`: modular analysis workflow (14 modules)
- `tests/`: pytest test suite with fixtures
- `context/contracts.md`: module contracts and canonical data contracts
- `context/data_dictionary.csv`: canonical dataset/column dictionary
- `outputs/`: generated artifacts only (ignored by git)
- `scripts/`: legacy R scripts (reference only, unchanged)

## Execution Order (Dependency Graph)
`00 -> 01 -> 01b -> 02 -> 02b -> 03 -> {04,05,06,07,09} -> 08 -> 10 -> 11`

Detailed dependencies:
- `00_data_inspection`: no dependencies
- `01_data_cleaning`: depends on `00`
- `01b_qc_after_cleaning`: depends on `01`
- `02_env_extraction`: depends on `01`
- `02b_qc_after_env_extraction`: depends on `02`
- `03_alpha_diversity`: depends on `02`
- `04_beta_diversity`: depends on `03`
- `05_cca_ordination`: depends on `02`
- `06_indicator_species`: depends on `03`
- `07_co_occurrence`: depends on `03`
- `08_evi_trends`: depends on `01`
- `09_sci_index`: depends on `03`
- `10_spatial_mapping`: depends on `03,04,08,09`
- `11_reporting`: depends on `03,04,05,06,07,08,09,10`

## Data Conventions
- CRS for point outputs: EPSG:4326
- Bhutan coordinate sanity bbox:
  - longitude: `88.7` to `92.2`
  - latitude: `26.7` to `28.4`
- Canonical datasets:
  - `outputs/processed_data/plot_points.gpkg` (GeoDataFrame POINT)
  - `outputs/processed_data/veg_long.csv`
  - `outputs/processed_data/sp_mat.rds` (pickle format)
  - `outputs/processed_data/env_master.csv`
- Forest type harmonization supports variants like `ForTyp`, `forest_type`, `foresttype`.

## Key Parameters
Configured in `python/config.py` under `config["params"]`:
- `seed`
- `permutations`
- `dpi`
- `cores`
- `min_species_occurrence`
- `min_group_size`
- `min_time_points`
- `outlier_iqr_multiplier`
- `correlation_flag_threshold`

## How To Run (Python, Windows/Linux)

### Prerequisites
Ensure Python 3.10+ is installed and dependencies are installed:
```bash
# Activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install package in editable mode
pip install -e .
```

### Environment setup
```python
from python.config import get_config
from python.setup import setup_project

setup_project()
config = get_config()
```

### Smoke test (module 00)
```bash
python -m python.run_pipeline --modules 00
```
Expected outputs:
- `outputs/data_inspection/data_inventory.csv`
- `outputs/data_inspection/data_inventory.txt`

### Run full pipeline
```bash
python -m python.run_pipeline
```

### Run subset
```bash
python -m python.run_pipeline --modules 01 02 03
python -m python.run_pipeline --from 03 --to 05
```

## Pipeline Execution Modes

### Parallel Execution (Default)
```bash
# Runs with automatic parallelization (recommended)
python -m python.run_pipeline --modules 03 04 05
# Modules at same dependency level run in parallel
# Uses ThreadPoolExecutor with auto-detected cores

# Full pipeline with parallel execution
python -m python.run_pipeline
```

### Preview Execution Plan
```bash
# Dry run: preview execution without running modules
python -m python.run_pipeline --dry-run

# Preview specific modules
python -m python.run_pipeline --modules 03 04 05 --dry-run

# Shows: execution levels, parallelism, time estimates, input status
```

### Continue on Error
```bash
# Continue executing independent modules even if some fail
python -m python.run_pipeline --continue-on-error

# Failed modules don't stop the pipeline
# Independent modules still execute
# Dependent modules are skipped with warnings
```

### Sequential Execution (Debugging)
```bash
# Force single-threaded execution
python -m python.run_pipeline --sequential

# Useful for debugging race conditions or comparing behavior
```

### Advanced Options
```bash
# Custom parallel workers (limit parallelism)
python -m python.run_pipeline --max-workers 2

# Combine flags
python -m python.run_pipeline --from 03 --to 08 --continue-on-error --log-level DEBUG

# Dry run with continue-on-error shows expected behavior
python -m python.run_pipeline --dry-run --continue-on-error
```

### Run tests
```bash
# Install test dependencies
pip install -e ".[test]"

# Run all tests
pytest tests/

# Run smoke tests only
pytest tests/test_smoke.py -v

# Run with coverage
pytest tests/ --cov=python --cov-report=term-missing
```

## Missing Input Behavior
- The pipeline never auto-downloads data.
- If a required input is missing, module stops with an explicit error and rerun instructions.
- For optional sources, module writes outputs with `NA` fields and records warnings.

## Reproducibility Logs
- Session info: `outputs/_run_logs/session_info.txt`
- Run manifest: `outputs/_run_logs/run_manifest.json`
- Pipeline logs: `outputs/_run_logs/pipeline_YYYYMMDD_HHMMSS.log`

## Troubleshooting

### Common Issues

**Module import errors:**
```bash
# Ensure you're running from project root and python/ is in path
cd "/mnt/e/NFI_Data/Forest Stratification and Vertical Zonation across Environmental Gradients in Bhutan"
python -m python.run_pipeline --modules 00
```

**Missing dependencies:**
```bash
# Reinstall all dependencies
pip install -e ".[test]"
```

**Permission errors on Windows:**
- Some file operations use atomic writes that may fail on Windows
- Check that output directories are not open in other programs
- Ensure you have write permissions to the outputs/ directory

**Log file location:**
- Check `outputs/_run_logs/` for detailed pipeline logs
- Each run creates a timestamped log file
- Use `--help` to see all CLI options

**Validation errors:**
- If a module reports validation errors, check the log file for details
- Validation errors indicate output files are missing, empty, or malformed
- Review the module's error traceback in the log file

## Performance Characteristics

### Full Pipeline Runtime
- **Sequential mode**: ~5.4 minutes (324 seconds)
- **Parallel mode** (default): ~2.8 minutes (170 seconds)
- **Speedup**: 1.91x (47.7% reduction)

### Execution Levels (Parallel Opportunities)
```
Level 0: 00                                    [1 module]
Level 1: 01                                    [1 module]
Level 2: 01b, 02, 08                           [3 parallel] ⚡
Level 3: 02b, 03, 05                           [3 parallel] ⚡
Level 4: 04, 06, 07, 09                        [4 parallel] ⚡
Level 5: 10                                    [1 module]
Level 6: 11                                    [1 module]
```

**Critical Path**: `00 → 01 → 02 → 03 → 04 → 10 → 11` (minimum ~170s)

### Module Runtime Profiles
- **Fast (<1s)**: 00, 01b, 02b
- **Moderate (1-5s)**: 03, 04, 05, 06, 07, 08, 09
- **Heavy (5-30s)**: 02 (rasterio sampling), 10 (geospatial I/O)

### Resource Tracking
- **Automatic monitoring**: Peak memory, CPU usage, elapsed time tracked per module
- **Logged at DEBUG level**: `--log-level DEBUG` to see resource reports
- **Included in manifest**: `run_manifest.json` contains `resources` field for each module
- **Requires**: `psutil` package (installed by default)

### Performance Tips
1. **Use parallel mode** (default) for production runs
2. **Limit workers** on resource-constrained systems: `--max-workers 2`
3. **Enable DEBUG logging** to identify bottlenecks: `--log-level DEBUG`
4. **Use dry-run** to preview execution plan: `--dry-run`
5. **Sequential mode** useful only for debugging, not performance

### Parallelization Safety
- ✅ **No write conflicts**: Each module has isolated output directory
- ✅ **No read locks**: Canonical files are read-only after creation
- ✅ **Thread-safe logging**: Python logging handles concurrent writes
- ✅ **No shared state**: Modules are pure functions of config
- ✅ **Deterministic**: Results identical to sequential execution
