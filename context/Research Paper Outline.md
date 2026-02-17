Research Paper Outline (Implementation-Aligned)
Title: Forest Stratification and Vertical Zonation of Bhutan Vegetation Using a Reproducible Python Workflow

1. Introduction
- Motivation: quantify vegetation stratification and environmental gradients across Bhutan.
- Data integration challenge: harmonize field vegetation records with multi-source geospatial covariates.
- Objective: produce reproducible biodiversity, community, and mapping outputs from a modular pipeline.

2. Materials and Methods
2.1 Study area and data sources
- Bhutan boundary, DEM, climate, forest type, soil, and EVI datasets in `raw_data/`.

2.2 Pre-processing
- Merge Trees/Shrubs/Herbs sheets.
- Standardize columns and taxon strings.
- Create canonical datasets: `veg_long`, `sp_mat`, `plot_points`.

2.3 Environmental extraction
- CRS-aware raster extraction for DEM and climate variables.
- Extract available BIO climate layers with canonical BIO1/BIO12 outputs.
- Forest and soil spatial joins.
- Slope/aspect derivation from DEM neighborhood gradients.

2.4 Analytical modules
- Alpha diversity: richness, Shannon, Simpson.
- Beta/community: NMDS + optional PERMANOVA text output.
- CCA ordination (Python implementation).
- Indicator species and co-occurrence networks.
- EVI trend classification using Theil-Sen + Mann-Kendall (plot-level only when plot IDs are present).
- EVI trend fallback path: nearest-plot assignment from coordinates, else country-level trend with optional replication to plot points for mapping continuity.
- SCI computation from normalized diversity components.

2.5 Spatial outputs and reporting
- Integrated spatial points and map layers.
- Automated report artifacts and run manifests.

3. Results (Expected from current pipeline)
- Diversity gradients and SCI distributions.
- NMDS/CCA structure and key indicator taxa.
- Network topology summaries.
- EVI trend summary (country-level for the current EVI file schema).
- Spatial visualization products in `outputs/spatial_maps/`.

4. Discussion
- Ecological interpretation of diversity and composition patterns.
- Data/model limitations driven by available input schema.
- Priority methodological extensions for future work.

5. Conclusion
- The repository now provides a coherent, reproducible Python workflow aligned with available data and generated outputs.

Planned Extensions (Future)
- GAM-based diversity modeling.
- Beta turnover/nestedness decomposition.
- Protected-area overlay once PA shapefile inputs are added.
