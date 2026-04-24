# Project Roadmap

## Vision

To establish the Bhutan Forest Stratification Pipeline as the **reference implementation** for National Forest Inventory analysis in the Hindu Kush-Himalayan region, enabling reproducible, standardized ecological assessments across countries.

---

## Version 1.0.0 (Current) - ✅ Complete

**Status:** Production Ready  
**Release Date:** 2026-03-08

### Core Features
- [x] 14 analysis modules implemented and tested
- [x] Parallel execution with dependency resolution
- [x] Module caching with smart invalidation
- [x] Comprehensive documentation (README, CONTRIBUTING, etc.)
- [x] CI/CD pipeline with GitHub Actions
- [x] Docker containerization
- [x] Pre-commit hooks for code quality
- [x] Test suite with 70%+ coverage target
- [x] Sphinx documentation infrastructure
- [x] Manuscript draft for *Science of the Total Environment*

---

## Version 1.1.0 (Q2 2026) - Enhanced Reporting

**Target Release:** 2026-06-01

### Interactive HTML Reports
- [ ] Plotly-based interactive figures
- [ ] Sortable, filterable data tables
- [ ] Downloadable outputs from report interface
- [ ] Executive summary dashboard

### Enhanced Visualization
- [ ] Interactive NMDS/CCA ordination plots
- [ ] Species distribution maps with leaflet
- [ ] Time-series EVI trend explorer
- [ ] Network visualization with Cytoscape.js

### Documentation
- [ ] Complete API documentation on ReadTheDocs
- [ ] Video tutorials for each module
- [ ] Jupyter notebook examples

---

## Version 1.2.0 (Q3 2026) - Data Management

**Target Release:** 2026-09-01

### Data Versioning
- [ ] DVC integration for input data tracking
- [ ] Automatic data checksums in run manifests
- [ ] Data lineage tracking

### Cloud Integration
- [ ] AWS S3 support for output storage
- [ ] Google Earth Engine integration for EVI
- [ ] Cloud-optimized GeoTIFF outputs

### Performance
- [ ] Dask integration for large datasets
- [ ] Out-of-core computation for species matrices
- [ ] Memory-mapped array support

---

## Version 1.3.0 (Q4 2026) - Extended Methods

**Target Release:** 2026-12-01

### Additional Analyses
- [ ] Phylogenetic diversity metrics
- [ ] Functional diversity indices
- [ ] Beta-diversity partitioning (Baselga framework)
- [ ] Multi-taxon analysis support

### Advanced Modeling
- [ ] Generalized Dissimilarity Modeling (GDM)
- [ ] Species Distribution Models (SDM)
- [ ] Random Forest variable importance

### Null Models
- [ ] Additional co-occurrence null models
- [ ] Phylogenetic community structure tests
- [ ] Trait-based assembly tests

---

## Version 2.0.0 (2027) - Multi-Region Support

**Target Release:** 2027-06-01

### Regional Expansion
- [ ] Support for Nepal NFI data format
- [ ] Support for India NFI data format
- [ ] Configurable regional parameters
- [ ] Multi-country comparative analysis

### Web Application
- [ ] Streamlit dashboard for non-technical users
- [ ] REST API for remote execution
- [ ] Job queue for batch processing
- [ ] User authentication and project management

### Database Integration
- [ ] PostgreSQL/PostGIS output option
- [ ] Direct database input support
- [ ] Automated database schema generation

---

## Long-Term Goals (2027+)

### Scientific Publications
- [ ] JOSS software paper submission
- [ ] Methods paper for *Ecography* or *Ecological Informatics*
- [ ] Application paper for Bhutan NFI analysis

### Community Building
- [ ] Workshop/tutorial at international conference
- [ ] Collaboration with ICIMOD
- [ ] Integration with GBIF data pipelines

### Sustainability
- [ ] Long-term maintenance plan
- [ ] Succession planning for lead developer
- [ ] Funding for continued development

---

## Known Limitations

### Current Version (1.0.0)

1. **Data Requirements**
   - Requires complete NFI dataset (not suitable for partial data)
   - No built-in data download capability
   - Large raster files must be pre-processed

2. **Performance**
   - Limited to single-machine execution
   - No GPU acceleration
   - Memory-intensive for >10,000 plots

3. **Methods**
   - CCA only (no alternative ordination methods)
   - Single co-occurrence metric
   - No temporal trend analysis for plot data

4. **Usability**
   - Command-line only (no GUI)
   - Requires Python knowledge for customization
   - Limited error recovery

---

## How to Contribute

We welcome contributions! See our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Priority Areas for Contribution

1. **Testing**
   - Additional unit tests for modules
   - Integration tests with sample data
   - Performance benchmarking

2. **Documentation**
   - Tutorial notebooks
   - Video screencasts
   - Translation to other languages

3. **Features**
   - Any items from the roadmap above
   - Bug fixes and performance improvements
   - New visualization types

4. **Bug Reports**
   - Issue reports on GitHub
   - Compatibility reports for different systems

---

## Funding & Support

This project is developed as part of a PhD research project at [Your University].

### Potential Funding Sources
- National Science Foundation (NSF)
- USAID Himalica Program
- World Bank Biodiversity Programs
- Global Environment Facility (GEF)

---

## Contact

For questions about the roadmap or to discuss collaborations:

- **Email:** your.email@university.edu
- **GitHub:** https://github.com/YOUR_USERNAME/bhutan-forest-stratification
- **Discussions:** https://github.com/YOUR_USERNAME/bhutan-forest-stratification/discussions

---

*Last updated: 2026-03-08*
