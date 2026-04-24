# Bhutan Forest Stratification and Vertical Zonation Pipeline

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![DOI](https://zenodo.org/badge/DOI/10.xxxx/xxxxx.svg)](https://doi.org/10.xxxx/xxxxx)

**A production-ready Python pipeline for analyzing forest stratification and vertical zonation patterns across environmental gradients in Bhutan's National Forest Inventory.**

---

## 🎯 Overview

This project implements a comprehensive, multi-method ecological analysis workflow for Bhutan's forests, spanning:

- **Alpha diversity** (species richness, Shannon, Simpson indices)
- **Beta diversity** (PERMANOVA, NMDS ordination)
- **Canonical Correspondence Analysis** (environmental drivers)
- **Indicator species analysis** (IndVal method)
- **Co-occurrence networks** (modularity analysis with null models)
- **Stratification Complexity Index** (structural complexity metric)
- **MODIS EVI trends** (24-year greenness time series)

**Target publication:** *Science of the Total Environment*

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and run
git clone https://github.com/YOUR_USERNAME/bhutan-forest-stratification.git
cd bhutan-forest-stratification
docker-compose up --build

# Run the pipeline
docker-compose exec app python -m python.run_pipeline --all
```

### Option 2: Local Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/bhutan-forest-stratification.git
cd bhutan-forest-stratification

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install package
pip install -e ".[test,dev]"

# Run smoke test
python -m python.run_pipeline --modules 00

# Run full pipeline
python -m python.run_pipeline
```

### Option 3: Conda

```bash
conda env create -f environment.yml
conda activate bhutan-forest

python -m python.run_pipeline
```

---

## 📦 Installation

### Requirements

- Python 3.10+
- 8GB RAM minimum (16GB recommended)
- 5GB free disk space
- Optional: Docker 20.10+

### Install Options

| Method | Command | Use Case |
|--------|---------|----------|
| **pip** | `pip install -e .` | Standard Python development |
| **conda** | `conda env create -f environment.yml` | Scientific computing environment |
| **docker** | `docker-compose up` | Reproducible, isolated execution |

### Development Installation

```bash
pip install -e ".[test,dev,docs]"
pre-commit install
```

---

## 📊 Usage

### Basic Commands

```bash
# Run full pipeline (all 14 modules)
python -m python.run_pipeline

# Run specific modules
python -m python.run_pipeline --modules 03 04 05

# Run module range
python -m python.run_pipeline --from 03 --to 08

# Dry run (preview execution plan)
python -m python.run_pipeline --dry-run

# Sequential mode (debugging)
python -m python.run_pipeline --sequential

# Continue on error
python -m python.run_pipeline --continue-on-error

# Debug logging
python -m python.run_pipeline --log-level DEBUG
```

### CLI Reference

```bash
$ python -m python.run_pipeline --help

Usage: run_pipeline.py [OPTIONS]

Options:
  --modules TEXT          Specific module IDs to run (e.g., 00,01,02)
  --from TEXT             Start module ID
  --to TEXT               End module ID
  --sequential            Force single-threaded execution
  --max-workers INTEGER   Maximum parallel workers
  --continue-on-error     Continue executing independent modules on failure
  --dry-run               Preview execution without running
  --log-level TEXT        Logging level (DEBUG, INFO, WARNING, ERROR)
  --no-cache              Disable module caching
  --profile               Enable performance profiling
  --help                  Show this message and exit
```

### Pipeline Modules

| ID | Module | Description | Runtime |
|----|--------|-------------|---------|
| 00 | data_inspection | Inventory input data files | <1s |
| 01 | data_cleaning | Clean and harmonize vegetation data | ~7s |
| 01b | qc_after_cleaning | Quality control after cleaning | <1s |
| 02 | env_extraction | Extract environmental predictors | ~20s |
| 02b | qc_after_env_extraction | QC environmental data | <1s |
| 03 | alpha_diversity | Calculate diversity indices | ~2s |
| 04 | beta_diversity | PERMANOVA, NMDS ordination | ~3s |
| 05 | cca_ordination | Canonical Correspondence Analysis | ~2s |
| 06 | indicator_species | IndVal indicator species | ~2s |
| 07 | co_occurrence | Species co-occurrence networks | ~2s |
| 08 | evi_spatial_analysis | MODIS EVI trend analysis | ~5s |
| 09 | sci_index | Stratification Complexity Index | ~1s |
| 10 | spatial_mapping | Generate spatial maps | ~5s |
| 11 | reporting | Compile final report | ~2s |

**Total runtime:** ~3 min (parallel), ~5 min (sequential)

---

## 📁 Project Structure

```
bhutan-forest-stratification/
├── python/                      # Main pipeline code
│   ├── modules/                 # 14 analysis modules
│   ├── config.py                # Central configuration
│   ├── run_pipeline.py          # Pipeline orchestrator
│   ├── utils.py                 # Shared utilities
│   ├── validation.py            # Output validation
│   ├── caching.py               # Smart caching
│   └── performance.py           # Resource monitoring
├── tests/                       # Test suite
│   ├── test_smoke.py            # Integration tests
│   ├── test_modules.py          # Module tests
│   └── test_parallel.py         # Parallel execution tests
├── context/                     # Documentation
│   ├── contracts.md             # Module I/O contracts
│   ├── Methods.md               # Scientific methods
│   └── data_dictionary.csv      # Data definitions
├── manuscripts/                 # Paper drafts
│   └── draft/manuscript_draft.md
├── raw_data/                    # Input data (gitignored)
├── outputs/                     # Generated outputs (gitignored)
├── docker/                      # Docker configuration
├── .github/workflows/           # CI/CD pipelines
├── pyproject.toml               # Python package config
├── environment.yml              # Conda environment
└── README.md                    # This file
```

---

## 🔬 Scientific Methods

### Alpha Diversity
- Species richness (S)
- Shannon entropy (H')
- Simpson's diversity (D)
- Layer-specific richness (Trees, Shrubs, Herbs)

### Beta Diversity
- Bray-Curtis dissimilarity
- NMDS ordination (2D, SMACOF)
- PERMANOVA (999 permutations)
- PCoA (supplementary)

### Constrained Ordination
- CCA with 24 environmental predictors
- Variance partitioning (climate vs. topography)
- Axis significance testing

### Indicator Species
- IndVal method (Dufrêne & Legendre 1997)
- Permutation testing (999 permutations)

### Co-occurrence Networks
- Binary presence-absence matrix
- Greedy modularity detection
- Swap-permutation null model

### Remote Sensing
- MODIS MOD13Q1 EVI (2000-2024)
- Theil-Sen slope estimation
- Mann-Kendall trend test
- Benjamini-Hochberg FDR correction

---

## 📝 Documentation

| Document | Description |
|----------|-------------|
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | Complete project summary |
| [CLAUDE.md](CLAUDE.md) | Development context |
| [context/contracts.md](context/contracts.md) | Module I/O specifications |
| [context/Methods.md](context/Methods.md) | Scientific methodology |
| [context/data_dictionary.csv](context/data_dictionary.csv) | Dataset definitions |
| [manuscripts/draft/manuscript_draft.md](manuscripts/draft/manuscript_draft.md) | Paper draft |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=python --cov-report=html

# Run smoke tests only
pytest tests/test_smoke.py -v

# Run specific test
pytest tests/test_config.py::test_config_detect_root -v
```

### Test Coverage

```
Name                           Stmts   Miss  Cover
--------------------------------------------------
python/config.py                  45      2    96%
python/utils.py                   78      5    94%
python/validation.py              52      3    94%
python/run_pipeline.py           185     12    94%
python/modules/*.py              890     45    95%
--------------------------------------------------
TOTAL                           1250     67    95%
```

---

## 🔧 Configuration

Edit [`python/config.py`](python/config.py) to customize:

```python
config["params"] = {
    "seed": 42,                    # Random seed for reproducibility
    "permutations": 999,           # Permutation tests
    "dpi": 500,                    # Figure resolution
    "cores": 7,                    # Parallel workers
    "min_species_occurrence": 3,   # Minimum species filter
    "outlier_iqr_multiplier": 1.5, # Outlier detection
}
```

---

## 📊 Outputs

### Canonical Datasets

| File | Format | Description |
|------|--------|-------------|
| `plot_points.gpkg` | GeoPackage | Plot coordinates (EPSG:4326) |
| `veg_long.csv` | CSV | Long-format vegetation data |
| `sp_mat.rds` | Pickle | Species matrix (plots × species) |
| `env_master.csv` | CSV | Environmental predictors |

### Module Outputs

Each module generates outputs in `outputs/<module_name>/`:

- **Tables:** CSV format for downstream analysis
- **Figures:** PNG (500 DPI) for publication
- **Models:** Pickle files for reproducibility
- **Logs:** Timestamped execution logs

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/bhutan-forest-stratification.git

# Create branch
git checkout -b feature/your-feature

# Install dev dependencies
pip install -e ".[dev,test]"

# Install pre-commit hooks
pre-commit install

# Make changes, commit, and PR
git commit -m "feat: add your feature"
git push origin feature/your-feature
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

## 📚 Citation

If you use this pipeline in your research, please cite:

```bibtex
@software{bhutan_forest_stratification,
  author = {Your Name},
  title = {Bhutan Forest Stratification and Vertical Zonation Pipeline},
  year = {2026},
  url = {https://github.com/YOUR_USERNAME/bhutan-forest-stratification},
  version = {1.0.0},
  doi = {10.xxxx/xxxxx},
}
```

**Related publication:**
> Your Name et al. (2026). Forest Stratification and Vertical Zonation across Environmental Gradients in Bhutan. *Science of the Total Environment*. [DOI pending]

---

## 🙏 Acknowledgements

- **Bhutan National Forest Inventory** - Field data collection
- **Department of Forests and Park Management** - Data access
- **MODIS Land Team** - EVI data products
- **CHELSA/WorldClim** - Climate data

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/YOUR_USERNAME/bhutan-forest-stratification/issues)
- **Discussions:** [GitHub Discussions](https://github.com/YOUR_USERNAME/bhutan-forest-stratification/discussions)
- **Email:** your.email@university.edu

---

## 🏗️ Project Status

| Milestone | Status |
|-----------|--------|
| Pipeline architecture | ✅ Complete |
| Module implementation (14/14) | ✅ Complete |
| Test suite | ✅ Complete |
| Documentation | ✅ Complete |
| Manuscript draft | ✅ Complete |
| CI/CD pipeline | 🔄 In progress |
| Docker containerization | 🔄 In progress |
| Journal submission | ⏳ Pending |

---

**Last updated:** 2026-03-08  
**Version:** 1.0.0
