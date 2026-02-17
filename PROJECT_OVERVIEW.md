# Bhutan Forest Stratification Project - Complete Overview

**Generated**: 2026-02-16
**Location**: `E:\NFI_Data\Forest Stratification and Vertical Zonation across Environmental Gradients in Bhutan`

---

## 🎯 Project Summary

This is a **production-ready Python pipeline** for analyzing forest stratification and vertical zonation patterns across environmental gradients in Bhutan. The project has been migrated from R to Python with significant architectural improvements.

**Current Status**: ✅ Partially executed (8/14 modules completed in last run)

---

## 📁 Directory Structure

```
E:\NFI_Data\Forest Stratification and Vertical Zonation across Environmental Gradients in Bhutan\
│
├── 📂 raw_data/                           # Input data (3.5 MB total)
│   ├── Vegetation Data.xlsx               # 3.5 MB - Main vegetation survey data
│   ├── MODIS_EVI_2000_2024_Bhutan.csv    # 49 KB - EVI time series
│   ├── Bhutan/                           # Bhutan boundary shapefile
│   ├── DEM_12/                           # Digital Elevation Model (12.5m)
│   │   └── DEM_Bhutan_12.5NG.tif
│   ├── Climate Rasters/                  # 19 bioclimatic variables (bio1-bio19)
│   │   └── Historical_1986-2015_bio*.tif
│   ├── FTM_distribution/                 # Forest Type Map
│   │   └── ForestTypeMap.shp
│   └── Soil Type Map_Bhutan/
│       ├── Raster file_Bhutan/Reclass_soiltype.tif
│       └── Shapefile_Bhutan/Bhutan Soil map.shp
│
├── 📂 python/                             # Main pipeline code
│   ├── config.py                         # Central configuration
│   ├── setup.py                          # Environment setup
│   ├── utils.py                          # Shared utilities
│   ├── validation.py                     # Output validation
│   ├── performance.py                    # Resource monitoring
│   ├── progress.py                       # Progress tracking
│   ├── caching.py                        # Data caching
│   ├── run_pipeline.py                   # Main orchestrator
│   └── modules/                          # 14 analysis modules
│       ├── 00_data_inspection.py
│       ├── 01_data_cleaning.py
│       ├── 01b_qc_after_cleaning.py
│       ├── 02_env_extraction.py
│       ├── 02b_qc_after_env_extraction.py
│       ├── 03_alpha_diversity.py
│       ├── 04_beta_diversity.py
│       ├── 05_cca_ordination.py
│       ├── 06_indicator_species.py
│       ├── 07_co_occurrence.py
│       ├── 08_evi_trends.py
│       ├── 09_sci_index.py
│       ├── 10_spatial_mapping.py
│       └── 11_reporting.py
│
├── 📂 outputs/                            # Generated outputs
│   ├── processed_data/                   # 19 files, 63 MB
│   │   ├── plot_points.gpkg             # Spatial points (EPSG:4326)
│   │   ├── veg_long.csv                 # Vegetation data (long format)
│   │   ├── sp_mat.rds                   # Species matrix (pickle)
│   │   ├── env_master.csv               # Environmental predictors
│   │   └── qc_*.csv                     # Quality control reports
│   ├── data_inspection/                  # 4 files
│   ├── alpha_diversity/                  # 4 files
│   ├── beta_diversity/                   # 3 files
│   ├── cca_ordination/                   # 3 files
│   ├── co_occurrence/                    # 3 files
│   ├── evi_trends/                       # 2 files
│   ├── indicator_species/                # 2 files
│   ├── sci_index/                        # 2 files
│   ├── spatial_maps/                     # 0 files (not yet run)
│   ├── reports/                          # 2 files
│   └── _run_logs/                        # 8 files
│       ├── run_manifest.json            # Execution metadata
│       ├── session_info.txt             # Environment info
│       └── pipeline_*.log               # Timestamped logs
│
├── 📂 tests/                              # Test suite
│   ├── conftest.py                       # Pytest fixtures
│   ├── test_config.py                    # Config tests
│   ├── test_utils.py                     # Utility tests
│   ├── test_smoke.py                     # Smoke tests
│   └── test_parallel.py                  # Parallel execution tests
│
├── 📂 context/                            # Documentation
│   ├── contracts.md                      # Module I/O contracts
│   ├── data_dictionary.csv              # Dataset/column definitions
│   ├── Methods.md                        # Scientific methods
│   └── Research Paper Outline.md        # Paper structure
│
├── 📂 .venv/                              # Python virtual environment
│
├── 📄 pyproject.toml                      # Python package configuration
├── 📄 CLAUDE.md                           # Main instructions (you read this)
├── 📄 Project Refinement Strategy.md      # Improvement roadmap
├── 📄 CHANGELOG.md                        # Version history
└── 📄 *.md                                # Various status/summary docs
```

---

## 🔧 System Configuration

**Python Environment**:
- Python: 3.12.3
- Package manager: pip 24.0
- Virtual environment: `.venv/` (exists, needs activation)
- Package: `bhutan-forest-stratification` v0.1.0

**Platform**:
- OS: Linux (WSL2) on Windows
- Shell: bash
- Working Directory: `/mnt/e/NFI_Data/Forest Stratification and Vertical Zonation across Environmental Gradients in Bhutan`

**Key Dependencies** (from pyproject.toml):
- numpy, pandas, scipy, scikit-learn, scikit-bio
- geopandas, rasterio, shapely
- matplotlib, networkx
- openpyxl (Excel support)
- tqdm (progress bars)
- psutil (resource monitoring)
- pytest, pytest-cov (testing)

---

## 🚀 How to Run (PowerShell)

### First Time Setup

```powershell
# Navigate to project
cd "E:\NFI_Data\Forest Stratification and Vertical Zonation across Environmental Gradients in Bhutan"

# Create virtual environment (if not exists)
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install package and dependencies
pip install -e .

# Install test dependencies (optional)
pip install -e ".[test]"
```

### Running the Pipeline

```powershell
# ALWAYS activate venv first (do this every time)
.venv\Scripts\Activate.ps1

# Quick smoke test (module 00 only)
python -m python.run_pipeline --modules 00

# Full pipeline (all 14 modules)
python -m python.run_pipeline

# Preview execution plan (dry run)
python -m python.run_pipeline --dry-run

# Run specific modules
python -m python.run_pipeline --modules 01 02 03

# Run range
python -m python.run_pipeline --from 03 --to 08

# Debug mode (sequential, verbose)
python -m python.run_pipeline --sequential --log-level DEBUG

# Continue on error
python -m python.run_pipeline --continue-on-error
```

### Checking Results

```powershell
# View latest log
Get-Content outputs\_run_logs\pipeline_*.log | Select-Object -Last 50

# View run manifest
Get-Content outputs\_run_logs\run_manifest.json

# Browse outputs
explorer outputs\
```

---

## 📊 Pipeline Module Workflow

**Execution Order** (with dependencies):

```
Level 0:  00_data_inspection
            ↓
Level 1:  01_data_cleaning
            ↓
Level 2:  01b_qc_after_cleaning  ← QC check
          02_env_extraction      ← Extract environmental vars
          08_evi_trends          ← EVI time series
            ↓
Level 3:  02b_qc_after_env_extraction  ← QC check
          03_alpha_diversity           ← Shannon, Simpson, etc.
          05_cca_ordination           ← CCA analysis
            ↓
Level 4:  04_beta_diversity      ← PERMANOVA, NMDS
          06_indicator_species   ← IndVal analysis
          07_co_occurrence       ← Network analysis
          09_sci_index           ← Species Composition Index
            ↓
Level 5:  10_spatial_mapping     ← Generate maps
            ↓
Level 6:  11_reporting           ← Final report
```

**Performance**:
- Sequential mode: ~5.4 minutes
- Parallel mode: ~2.8 minutes (1.91x speedup)
- Modules with same dependency level run in parallel automatically

---

## 📝 Last Pipeline Run

**Date**: 2026-02-16 16:21:33 +0600
**Mode**: Parallel (7 workers)
**Status**: ❌ Failed (incomplete)
**Modules Completed**: 8/14

✅ **Completed**:
- 00_data_inspection (0.11s)
- 01_data_cleaning (6.99s)
- 01b_qc_after_cleaning (0.41s)
- 02_env_extraction
- 02b_qc_after_env_extraction
- 03_alpha_diversity
- 05_cca_ordination
- 08_evi_trends

❌ **Not Run**:
- 04_beta_diversity
- 06_indicator_species
- 07_co_occurrence
- 09_sci_index
- 10_spatial_mapping
- 11_reporting

**Key Outputs Created**:
- `plot_points.gpkg` - 324 KB spatial data
- `veg_long.csv` - 7.7 MB vegetation data
- `sp_mat.rds` - 33 MB species matrix
- `env_master.csv` - 1.2 MB environmental predictors

---

## 🎓 Scientific Methods

The pipeline implements these ecological analyses:

1. **Alpha Diversity**: Shannon, Simpson, richness indices
2. **Beta Diversity**: PERMANOVA, NMDS ordination
3. **CCA Ordination**: Canonical Correspondence Analysis
4. **Indicator Species**: IndVal method
5. **Co-occurrence Networks**: Species association graphs
6. **EVI Trends**: MODIS Enhanced Vegetation Index time series
7. **SCI Index**: Species Composition Index
8. **Spatial Mapping**: GIS-based visualization

See `context/Methods.md` for detailed methodology.

---

## 🔍 Key Features

✅ **Implemented**:
- ✅ Parallel execution with automatic dependency resolution
- ✅ Resource monitoring (CPU, memory, runtime)
- ✅ Data validation and QC checks
- ✅ Structured logging with timestamps
- ✅ Run manifests for reproducibility
- ✅ Modular architecture with clean contracts
- ✅ Test suite (pytest)
- ✅ CRS validation (EPSG:4326)
- ✅ Deterministic results (seed=42)
- ✅ Dry-run mode for planning
- ✅ Continue-on-error for robustness

⏳ **Planned** (from Project Refinement Strategy):
- Data schema validation (pandera/pydantic)
- Caching with invalidation
- HTML dashboard reporting
- Interactive plots (plotly)
- Containerization (Docker)
- CI/CD pipeline
- Git commit tracking in manifests

---

## 🐛 Troubleshooting

**Problem**: `python: command not found`
**Solution**: Use `python3` instead, or create alias in PowerShell:
```powershell
Set-Alias python python3
```

**Problem**: Module import errors
**Solution**: Ensure you're in project root and venv is activated:
```powershell
cd "E:\NFI_Data\Forest Stratification and Vertical Zonation across Environmental Gradients in Bhutan"
.venv\Scripts\Activate.ps1
```

**Problem**: Permission errors on Windows
**Solution**:
- Close any programs that have output files open
- Run PowerShell as Administrator
- Check write permissions on `outputs/` directory

**Problem**: Missing dependencies
**Solution**: Reinstall:
```powershell
pip install -e ".[test]" --force-reinstall
```

**Problem**: Pipeline fails mid-run
**Solution**: Check logs for details:
```powershell
Get-Content outputs\_run_logs\pipeline_*.log | Select-Object -Last 100
```

---

## 📚 Important Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Main project instructions (Claude Code context) |
| `pyproject.toml` | Python package configuration |
| `python/config.py` | Central configuration (paths, parameters) |
| `python/run_pipeline.py` | Pipeline orchestrator |
| `context/contracts.md` | Module I/O specifications |
| `context/data_dictionary.csv` | Dataset documentation |
| `outputs/_run_logs/run_manifest.json` | Last execution record |
| `Project Refinement Strategy.md` | Improvement roadmap |

---

## 🔬 Data Contracts

**Key Datasets** (canonical):

1. **plot_points.gpkg**
   - Type: GeoPackage (spatial points)
   - CRS: EPSG:4326
   - Columns: `plot_id`, `longitude`, `latitude`

2. **veg_long.csv**
   - Type: Long-format vegetation data
   - Columns: `plot_id`, `species_name`, `stratum`, `abundance`

3. **sp_mat.rds**
   - Type: Pickle (Python object)
   - Shape: plots × species matrix
   - Values: abundance or presence/absence

4. **env_master.csv**
   - Type: Plot-level environmental predictors
   - Columns: `plot_id`, `elevation`, `slope`, `aspect`, `bio*`, `soil_type`, `forest_type`

---

## 🎯 Next Steps

To resume analysis:

1. **Run remaining modules**:
   ```powershell
   .venv\Scripts\Activate.ps1
   python -m python.run_pipeline --from 04
   ```

2. **Run full pipeline from scratch**:
   ```powershell
   python -m python.run_pipeline
   ```

3. **Run tests**:
   ```powershell
   pytest tests/ -v
   ```

4. **Generate HTML report** (after module 11 completes):
   - Check `outputs/reports/` for generated markdown
   - Convert to HTML using pandoc or similar

---

## 📞 Getting Help

- `/help` - Claude Code help
- `python -m python.run_pipeline --help` - CLI options
- GitHub issues: https://github.com/anthropics/claude-code/issues
- Check logs: `outputs/_run_logs/`

---

**Generated by Claude Code** | 2026-02-16
