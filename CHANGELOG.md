# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (1st revision — reviewer responses)
- **A2/B3** `04_beta_diversity`: NMDS `n_init` raised 4→20 (matches vegan::metaMDS); PERMDISP2 (Anderson 2006 permutation F-test) replaces K-W proxy
- **B1** `04_beta_diversity`: Mantel test (Bray-Curtis vs Haversine geographic distance); outputs `mantel_test_results.csv`
- **A11** `04_beta_diversity`: PCoA axis labels now show "% of total variation"; outputs `pcoa_axis_summary.csv`
- **A3** `05_cca_ordination`: Aspect decomposed into `aspect_northness`/`aspect_eastness` (circular transformation, Pewsey & García-Portugués 2021)
- **A4** `05_cca_ordination`: Shared variance fraction (topo ∩ climate) added to `variance_partitioning.csv` (Borcard et al. 1992)
- **A8** `05_cca_ordination`: CCA axis table now includes `pct_constrained` and `pct_total` (% of total chi-square inertia)
- **B2** `03_alpha_diversity`: Dunn's post-hoc pairwise test (BH-FDR) after Kruskal-Wallis; outputs `elevation_band_dunn_posthoc.csv`
- **A5** `07_co_occurrence`: CNM community detection replaced with Louvain (`networkx.louvain_communities`); null model updated for consistency
- **B4** `07_co_occurrence`: Hypergeometric per-pair co-occurrence significance test (BH-FDR); outputs `co_occurrence_edges_hypergeometric.csv`
- **A6** `08_evi_spatial_analysis`: Tie-corrected Mann-Kendall variance function `_mk_var_with_ties()` added; tie fraction reported when EVI stack available
- **B5** `08_evi_spatial_analysis`: Moran's I spatial autocorrelation (rook contiguity, 3 lag distances) on subsampled MK p-value raster; outputs `morans_i_results.csv`
- **A9** `09_sci_index`: SE and 95% CI added to forest-type SCI summary; small-sample groups (n<30) flagged; outputs `sci_forest_type_summary.csv`
- **pyproject.toml / environment.yml**: Added `scikit-posthocs>=0.8.0`

### Changed (1st revision)
- **A1** `03_alpha_diversity`: Effect size key renamed `eta_squared` → `epsilon_squared` (formula `(H-k+1)/(n-k)` is ε², not η²)
- **A7** `04_beta_diversity`: PERMANOVA R² stored to 4 decimal places in summary CSV
- **A10** `08_evi_spatial_analysis`: EVI correlation annotations changed from Pearson r to Spearman ρ throughout (slope-elevation, slope-richness, slope-SCI, integrated panel)

### Added
- Docker containerization with multi-stage build
- Docker Compose configuration for development, Jupyter, and documentation
- Comprehensive CI/CD pipeline with GitHub Actions
- Pre-commit hooks for code quality (black, isort, flake8, mypy, bandit)
- CODE_OF_CONDUCT.md and SECURITY.md
- CONTRIBUTING.md with development guidelines
- CITATION.cff for academic citation
- environment.yml for conda users
- GitHub issue and pull request templates
- Sphinx documentation configuration

### Changed
- Updated pyproject.toml with full metadata, classifiers, and tool configuration
- Enhanced README.md with comprehensive documentation
- Improved CI workflow with multi-OS, multi-Python testing

### Fixed
- Module 08 naming consistency (evi_spatial_analysis)

## [1.0.0] - 2026-03-08

### Added
- **Full pipeline implementation** with 14 analysis modules:
  - 00_data_inspection - Data inventory and validation
  - 01_data_cleaning - Vegetation data cleaning and harmonization
  - 01b_qc_after_cleaning - Quality control after cleaning
  - 02_env_extraction - Environmental variable extraction
  - 02b_qc_after_env_extraction - QC environmental data
  - 03_alpha_diversity - Species diversity indices
  - 04_beta_diversity - PERMANOVA, NMDS ordination
  - 05_cca_ordination - Canonical Correspondence Analysis
  - 06_indicator_species - IndVal indicator species analysis
  - 07_co_occurrence - Species co-occurrence networks
  - 08_evi_spatial_analysis - MODIS EVI trend analysis
  - 09_sci_index - Stratification Complexity Index
  - 10_spatial_mapping - Spatial visualization
  - 11_reporting - Final report generation

- **Pipeline infrastructure**:
  - Parallel execution with automatic dependency resolution
  - Module caching with smart invalidation
  - Resource monitoring (CPU, memory, runtime)
  - Comprehensive logging with timestamps
  - Run manifests for reproducibility
  - Output validation layer
  - Dry-run mode for planning
  - Continue-on-error for robustness

- **Testing**:
  - Pytest test suite with smoke tests
  - Integration tests for module contracts
  - Test fixtures and conftest configuration

- **Documentation**:
  - PROJECT_OVERVIEW.md - Complete project summary
  - CLAUDE.md - Development context
  - context/contracts.md - Module I/O specifications
  - context/Methods.md - Scientific methodology
  - context/data_dictionary.csv - Dataset definitions
  - Manuscript draft for Science of the Total Environment

### Scientific Methods Implemented
- Alpha diversity (Shannon, Simpson, richness)
- Beta diversity (PERMANOVA, NMDS, PCoA)
- CCA ordination with variance partitioning
- Indicator species (IndVal method)
- Co-occurrence networks with null models
- MODIS EVI trends (Theil-Sen, Mann-Kendall, FDR correction)
- Stratification Complexity Index

### Technical Features
- Centralized configuration with case-insensitive paths
- Canonical column name mappings
- CRS validation (EPSG:4326)
- Deterministic results (seed=42)
- Atomic file writes
- Progress bars for long operations

## [0.1.0] - 2026-02-13

### Added
- Initial project structure
- Migration from R to Python begun
- Basic pipeline orchestration
- Module registry and dependency handling

---

## Version History

| Version | Date | Status |
|---------|------|--------|
| 1.0.0 | 2026-03-08 | Production ready |
| 0.1.0 | 2026-02-13 | Initial development |

---

## Upcoming (v1.1.0)

### Planned Features
- Interactive HTML reports with Plotly
- DVC data versioning integration
- Enhanced unit test coverage (>80%)
- Sphinx API documentation
- Performance optimization for large datasets
- Additional null models for co-occurrence analysis

### Under Consideration
- Streamlit dashboard for interactive exploration
- REST API for remote execution
- Cloud deployment (AWS/GCP)
- Integration with R via rpy2

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

## Citation

If you use this software in your research, please cite it as described in [CITATION.cff](CITATION.cff).
