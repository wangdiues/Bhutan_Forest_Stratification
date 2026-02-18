# Research Article Plan

**Title:**
Forest Stratification and Vertical Zonation across Environmental Gradients in Bhutan: Diversity Patterns, Community Assembly, and Long-Term Greenness Trends from the National Forest Inventory

**Alternative title:**
Altitudinal Drivers of Forest Diversity and Structure in the Eastern Himalayas: A Multi-Method Analysis of Bhutan's National Forest Inventory

**Date drafted:** 2026-02-18
**Last updated:** 2026-02-18 (pipeline finalised; all figures regenerated at publication quality)

---

## Target Journal

**Primary:** Forest Ecology and Management (Elsevier, IF ≈ 4.2)
Word limit: ~8,000 words | Structured sections | Open data encouraged

**Backup:** Ecological Indicators (IF ≈ 6.9) — if SCI metric is framed as the centrepiece

---

## Author Structure (suggested)

Lead author → NFI data custodian / analyst
Co-authors → ecologists, remote sensing specialist, forest policy contributor
Corresponding author → institutional affiliation with Bhutan NFI programme

---

## Abstract (250 words)

Bhutan's forests span one of the steepest unbroken altitudinal gradients in the Eastern Himalayas (113–5,469 m), yet a country-wide, multi-method characterisation of their vertical stratification remains absent. Using 1,942 systematically distributed National Forest Inventory (NFI) plots, we quantified alpha diversity, beta diversity turnover, environmental drivers of community assembly, indicator species, co-occurrence network structure, structural complexity, and long-term vegetation greenness trends. Species richness declined monotonically from lowland forest (24.8 ± 9.0 spp at 500–1,000 m) to alpine scrub (8.9 ± 5.6 spp above 4,000 m), and varied substantially among 12 forest types (range: 8.2 in Dry Alpine Scrub to 26.0 in Subtropical Forest). NMDS ordination revealed a primary compositional gradient separating subtropical broadleaf assemblages from subalpine conifer and alpine shrub communities, consistent with canonical correspondence analysis (CCA) identifying cold-season temperature (bio11) and warmest-quarter temperature (bio10) as dominant community-assembly drivers. Indicator species analysis confirmed 410 significant taxon–habitat associations (all p ≤ 0.05) spanning iconic species such as *Pinus roxburghii* (Chirpine Forest, IndVal = 0.794) and *Rhododendron anthopogon* (Dry Alpine Scrub, IndVal = 0.283). Co-occurrence network analysis recovered 1,115 species nodes, 29,854 positive co-occurrence edges, and three distinct community modules corresponding to lowland, montane, and subalpine assemblages. The Stratification Complexity Index was highest in subtropical and warm broadleaved forests (SCI = +4.49 and +3.84, respectively) and lowest in alpine scrubland (−5.44). Spatially-explicit MODIS EVI trend analysis (2000–2024) revealed that 42.9% of Bhutan's forested area experienced significant greening (p ≤ 0.05, Mann-Kendall), with only 1.3% showing significant browning. Greening intensity was strongest at low elevations (500–1,000 m: mean Theil-Sen slope = 0.00164 EVI yr⁻¹; 61.8% significantly greening) and weakest in montane-subalpine zones (3,000–3,500 m: 0.00064 EVI yr⁻¹; 22.8% significantly greening). EVI trend slope correlated positively with species richness across plots (Pearson r = 0.105, p < 0.001). Together, these findings establish a reproducible, open-source baseline for long-term biodiversity monitoring and climate-adaptive forest management in Bhutan.

**Keywords:** altitudinal zonation; vertical stratification; species richness; NMDS; CCA; indicator species; co-occurrence network; stratification complexity index; MODIS EVI; Eastern Himalayas; National Forest Inventory

---

## 1. Introduction (~900 words)

**¶1 — Global framing**
Mountain forests cover ~28% of global forested area but harbour disproportionate biodiversity due to compressed environmental gradients. The Himalayas are among the world's most important biodiversity hotspots (Myers et al. 2000). Climate change is altering altitudinal vegetation zones faster than lowland systems (Pepin et al. 2015), making baseline characterisation urgent.

**¶2 — Bhutan's unique position**
Bhutan retains >70% forest cover under a constitutional mandate; its forests span subtropical foothills to alpine treelines within <150 km horizontal distance — one of the steepest biotic gradients on Earth. This makes it an ideal natural laboratory for studying altitude-driven forest stratification, yet no country-wide, multi-method study exists.

**¶3 — Specific knowledge gaps**
- The relationship between forest vertical zonation and multi-scale environmental gradients (elevation, temperature seasonality, precipitation) has not been quantified at the national scale using field inventory data
- Species co-occurrence network structure and community modularity in Himalayan forests remain largely undescribed
- Forest structural complexity (multi-layer stratification) has not been spatially mapped or linked to environmental gradients in Bhutan

**¶4 — Study objectives**
1. Quantify alpha diversity (richness, Shannon H, layer-specific richness) across the full elevational gradient
2. Characterise beta diversity turnover (NMDS) and identify primary environmental drivers of community assembly (CCA)
3. Identify indicator taxa diagnostic of each forest zone
4. Describe co-occurrence network topology and community modularity
5. Compute a Stratification Complexity Index (SCI) integrating multi-layer structural information
6. Assess 24-year spatially-explicit vegetation greenness trend (per pixel and per plot) and link it to elevation zone and forest type using MODIS EVI raster data

**¶5 — Novelty and significance**
First integrated, country-scale, multi-method synthesis of Bhutan's forest vertical zonation using NFI; provides a fully reproducible open-source analysis pipeline; directly relevant to Bhutan's REDD+ commitments and National Biodiversity Strategy.

---

## 2. Materials and Methods

### 2.1 Study Area

Bhutan (26.7°–28.4°N, 88.7°–92.2°E; 38,394 km²), eastern Himalayas. Elevation 113–7,570 m. Five climatic zones (subtropical to alpine). Twelve classified forest types from subtropical to alpine. Map: Fig. 1.

### 2.2 National Forest Inventory Dataset

- Design: systematic sampling grid, **n = 1,942 plots** (Fig. 1)
- Variables: species identity and cover by vertical layer (Trees, Shrubs, Herbs), plot area (ha), forest type, soil type, district (Dzongkhag)
- Elevation range: **113–5,469 m** (mean 2,454 ± 1,271 m)
- Data cleaning: duplicate removal, coordinate sanity checks (Bhutan bbox), species name normalisation

### 2.3 Environmental Variable Extraction

Extracted at each plot centroid via bilinear resampling (rasterio):

- **Topography:** elevation (m), slope (°), aspect (°) from SRTM DEM
- **Climate:** WorldClim v2 BioClim variables (bio1–bio19); focal variables: bio1 (MAT), bio11 (mean temperature coldest quarter), bio10 (mean temperature warmest quarter), bio12 (MAP), bio4 (temperature seasonality)
- **Soil:** FAO soil type class

### 2.4 Alpha Diversity

- Per plot: species richness (S), Shannon H (natural log), Simpson D
- Layer-specific richness: Trees, Shrubs, Herbs
- Analysed by forest type and 500-m elevation bands (<500 to >4,000 m)

### 2.5 Beta Diversity — NMDS Ordination

- Species matrix: plots × species (minimum occurrence filter applied)
- Bray-Curtis dissimilarity; 2-dimensional non-metric MDS (sklearn SMACOF, 4 random starts, max 300 iterations, seed = 42)
- `sklearn MDS.stress_` = 0.338 — **this is sklearn's raw residual stress, NOT Kruskal's normalized stress-1**; the standard ecological thresholds (< 0.10 good, > 0.30 poor) apply only to Kruskal stress-1 and cannot be applied here
- The compositional gradient is independently confirmed by PERMANOVA (pseudo-F = 17.03, p = 0.001, 999 permutations), which operates directly on the Bray-Curtis distance matrix and does not depend on ordination quality
- For final submission: **replace sklearn MDS with vegan `metaMDS`** (999 random starts, convergence-tested) to report proper Kruskal stress-1 and meet reviewer expectations for ecology journals
- Forest type centroids and NMDS1 gradient mapped spatially

### 2.6 Canonical Correspondence Analysis

- CCA of species matrix constrained by: elevation, bio1, bio10, bio11, bio12, soil type
- Biplot scores reported for CCA1 and CCA2
- Permutation test for axis significance (n = 999)

### 2.7 Indicator Species Analysis

- IndVal method (Dufrêne & Legendre 1997)
- Groups: 12 forest types
- Significance: p ≤ 0.05 (999 permutations)
- Report top three indicators per forest type

### 2.8 Co-occurrence Network Analysis

- Presence-absence co-occurrence matrix across 1,942 plots
- **1,115 species nodes**, **29,854 co-occurrence edges** (edge weight = shared plot count)
- Node metrics: degree, betweenness centrality
- Community detection: modularity-optimised algorithm
- Hub species: top betweenness centrality

### 2.9 Stratification Complexity Index (SCI)

- Components: z-standardised richness (total, Trees, Shrubs, Herbs), Shannon H, Simpson D
- SCI = sum of z-scores (range: −15.15 to +25.15)
- Analysed by forest type and elevation; mapped spatially (Fig. 6)

### 2.10 Spatially-Explicit EVI Trend Analysis

- **Data:** Google Earth Engine exports of MODIS MOD13Q1 (V061) at native 250 m resolution, 2000–2024:
  - Theil-Sen slope raster (GeoTIFF, ~250 m pixel; 684,055 valid pixels = 42,754 km²)
  - Mann-Kendall tau raster (2 bands: tau, p-value); where GEE p-value band was all NaN, p-values derived analytically from tau using normal approximation: Var(S) = n(n−1)(2n+5)/18, Z = (S∓1)/√Var(S), p = 2(1−Φ(|Z|)), n = 25 years
  - Annual EVI stack (25 bands, 2000–2024)
- **Per-plot extraction:** Theil-Sen slope and MK tau sampled at each NFI plot centroid (rasterio)
- **Pixel-level classification:** Significant greening (slope > 0, p ≤ 0.05), significant browning (slope < 0, p ≤ 0.05), stable/non-significant
- **Pixel area:** calculated from raster resolution (degrees × 111,320 m deg⁻¹)² ÷ 10⁶
- **Stratified summaries:** mean slope and % significantly greening by 500-m elevation band and by forest type
- **Richness linkage:** Pearson r between per-plot EVI slope and species richness

### 2.11 Reproducibility

Python 3.12 open-source pipeline; fixed seed; all outputs versioned. Code: [GitHub URL].

---

## 3. Results

### 3.1 Alpha Diversity across Elevation and Forest Type

**Elevation gradient (Table 1, Fig. 2):**

| Elevation band | n plots | Mean richness | SD |
|---|---|---|---|
| < 500 m | 103 | 22.9 | 10.4 |
| 500–1,000 m | 171 | **24.8** | 9.0 |
| 1,000–1,500 m | 249 | 21.0 | 9.5 |
| 1,500–2,000 m | 255 | 21.6 | 9.3 |
| 2,000–2,500 m | 258 | 17.6 | 7.2 |
| 2,500–3,000 m | 253 | 16.0 | 6.0 |
| 3,000–3,500 m | 204 | 14.2 | 5.6 |
| 3,500–4,000 m | 164 | 11.1 | 5.8 |
| > 4,000 m | 285 | 8.9 | 5.6 |

Species richness peaked at 500–1,000 m and declined monotonically towards the alpine zone — a 2.8× reduction from peak to highest elevations. Overall: mean = 17.1 ± 9.1 spp/plot, range 1–57.

**By forest type:** Subtropical Forest (26.0 ± 8.7) and Warm Broadleaved Forest (24.2 ± 8.5) were most species-rich; Dry Alpine Scrub (8.2 ± 4.7) and Chirpine Forest (11.6 ± 7.1) least.

**Layer richness:** Trees contributed the largest share of richness (mean 9.1 ± 7.3 spp), followed by Shrubs (5.5 ± 4.2) and Herbs (2.8 ± 3.2).

### 3.2 Beta Diversity and Community Turnover (Fig. 3)

Non-metric MDS ordination (2D, Bray-Curtis dissimilarity; sklearn `stress_` = 0.338, a raw residual metric not equivalent to Kruskal's stress-1) revealed a clear primary compositional axis (NMDS1) separating subtropical and warm broadleaved assemblages (NMDS1 means: +0.49, +0.49) from subalpine communities — Juniper-Rhododendron Scrub (−0.62), Dry Alpine Scrub (−0.58), Fir Forest (−0.57). NMDS2 reflects a secondary moisture or disturbance gradient. Compositional differentiation among the 12 forest types was confirmed independently by PERMANOVA (pseudo-F = 17.03, p = 0.001, 999 permutations), which is unaffected by ordination distortion. *(Note for revision: replace sklearn MDS with vegan metaMDS to report proper Kruskal stress-1.)*

**NMDS1 means by forest type:**

| Forest type | NMDS1 mean |
|---|---|
| Juniper Rhododendron Scrub | −0.617 |
| Dry Alpine Scrub | −0.576 |
| Fir Forest | −0.565 |
| Blue Pine Forest | −0.408 |
| Spruce Forest | −0.387 |
| Hemlock Forest | −0.326 |
| Evergreen Oak Forest | +0.079 |
| Cool Broadleaved Forest | +0.188 |
| Chirpine Forest | +0.277 |
| Subtropical Forest | +0.488 |
| Warm Broadleaved Forest | +0.493 |

### 3.3 Environmental Drivers of Community Assembly (Fig. 4)

CCA identified the dominant environmental gradient along CCA2:

| Variable | CCA2 score | Interpretation |
|---|---|---|
| bio11 (coldest quarter temp.) | +0.610 | Strongest driver |
| bio10 (warmest quarter temp.) | −0.557 | Opposing gradient |
| bio1 (MAT) | +0.191 | |
| bio12 (MAP) | +0.158 | |
| elevation | +0.145 | |

Temperature seasonality — the contrast between warmest and coldest quarters — is the primary axis structuring Bhutan's forest communities, consistent with its role in defining treeline and cold-season stress tolerance limits.

### 3.4 Indicator Species by Forest Zone (Table 2)

| Forest zone | Top indicator species | IndVal | p |
|---|---|---|---|
| Chirpine Forest | *Pinus roxburghii* | 0.794 | 0.005 |
| Spruce Forest | *Picea spinulosa* | 0.463 | 0.005 |
| Blue Pine Forest | *Pinus wallichiana* | 0.411 | 0.005 |
| Fir Forest | *Abies densa* | 0.387 | 0.005 |
| Subtropical Forest | *Pterospermum acerifolium* | 0.314 | 0.005 |
| Evergreen Oak Forest | *Quercus lamellosa* | 0.301 | 0.005 |
| Hemlock Forest | *Tsuga dumosa* | 0.286 | 0.005 |
| Dry Alpine Scrub | *Rhododendron anthopogon* | 0.283 | 0.005 |
| Warm Broadleaved Forest | *Maesa chisia* | 0.173 | 0.005 |
| Cool Broadleaved Forest | *Elatostema* sp. | 0.089 | 0.005 |
| Juniper Rhododendron Scrub | *Juniperus recurva* | 0.102 | 0.010 |
| Chirpine Forest (2nd) | *Indigofera dosua* | 0.496 | 0.005 |

Total significant indicators: **410** (all p ≤ 0.05). Conifers showed the strongest IndVal scores, reflecting high habitat fidelity.

### 3.5 Co-occurrence Network Structure (Fig. 5)

The species co-occurrence network comprised **1,115 nodes** and **29,854 edges** (mean degree = 53.5, range 1–738). Three distinct community modules were detected:

| Module | Species count |
|---|---|
| 1 (lowland broadleaf) | 523 |
| 2 (montane mixed) | 461 |
| 3 (subalpine/alpine) | 131 |

Hub species with highest betweenness centrality: *Maesa chisia* (degree = 550), *Ficus* sp. (degree = 510), *Acer campbellii* (degree = 296).

### 3.6 Stratification Complexity Index (Fig. 6)

SCI ranged from −15.15 to +25.15 (mean = 0, SD = 5.88).

| Forest type | Mean SCI | SD |
|---|---|---|
| Subtropical Forest | +4.49 | 5.17 |
| Warm Broadleaved Forest | +3.84 | 5.13 |
| Spruce Forest | +1.86 | 4.11 |
| Cool Broadleaved Forest | +0.70 | 4.80 |
| Blue Pine Forest | +0.24 | 4.25 |
| Evergreen Oak Forest | +0.11 | 4.26 |
| Hemlock Forest | −0.24 | 4.42 |
| Chirpine Forest | −3.01 | 5.53 |
| Fir Forest | −3.11 | 4.27 |
| Non Forest | −3.13 | 6.14 |
| Juniper Rhododendron Scrub | −3.78 | 5.06 |
| Dry Alpine Scrub | −5.44 | 4.36 |

### 3.7 Spatially-Explicit EVI Trend Patterns, 2000–2024 (Figs. 7–9)

Pixel-level Mann-Kendall trend classification of the full MODIS EVI record (2000–2024) across Bhutan's 42,754 km² of valid forest area revealed substantial spatial heterogeneity in long-term greenness dynamics:

**Areal classification (Table 4, Fig. 7):**

| Trend class | Area (km²) | % of valid area |
|---|---|---|
| Significant greening (p ≤ 0.05) | 18,345 | **42.9%** |
| Stable / non-significant | 23,852 | 55.8% |
| Significant browning (p ≤ 0.05) | 556 | 1.3% |

Nearly half of Bhutan's forest area is experiencing a statistically significant positive EVI trend; browning is spatially rare.

**Elevation gradient (Fig. 8):**

| Elevation band | Mean slope (EVI yr⁻¹) | % sig. greening |
|---|---|---|
| < 500 m | 0.00184 | 68.1% |
| 500–1,000 m | 0.00164 | **61.8%** |
| 1,000–1,500 m | 0.00155 | 57.0% |
| 1,500–2,000 m | 0.00147 | 52.8% |
| 2,000–2,500 m | 0.00087 | 30.1% |
| 2,500–3,000 m | 0.00088 | 31.5% |
| 3,000–3,500 m | 0.00064 | 22.8% |
| 3,500–4,000 m | 0.00063 | 19.6% |
| > 4,000 m | 0.00162 | 43.8% |

Greening was strongest and most significant at low elevations (< 1,500 m), declining sharply through the montane zone (2,000–4,000 m) before recovering at the highest elevations (> 4,000 m; alpine scrub expansion).

**By forest type (Fig. 8):**

Warm Broadleaved (94.1% greening), Subtropical (94.2%), and Dry Alpine Scrub (94.3%) showed the highest proportion of greening pixels; Spruce Forest (57.1%) and Blue Pine Forest (63.0%) showed the lowest.

**Richness correlation (Fig. 9):**

Per-plot EVI slope correlated positively with species richness across all 1,910 plots with valid EVI data (Pearson r = 0.105, p < 0.001), indicating that areas of stronger vegetation greening also tend to support more plant species — consistent with the productivity-diversity hypothesis.

---

## 4. Discussion (~1,200 words)

**¶1 — Monotonic richness decline (not hump-shaped)**
The elevation–richness relationship shows a monotonic decline above 1,000 m rather than a classic mid-domain hump. This contrasts with some Himalayan studies (Grytnes & Vetaas 2002) but is consistent with the high productivity of Bhutan's warm, wet subtropical lowlands. Lowland agriculture-forest boundaries may maintain edge diversity, inflating low-elevation richness.

**¶2 — Temperature seasonality as primary community driver**
The dominance of bio11 and bio10 on CCA2 points to cold-season temperature stress — not mean annual temperature or precipitation alone — as the key filter separating forest assemblages. This is consistent with cold hardiness as the primary trait axis in Himalayan trees (Körner 2012) and with treeline being thermally rather than hydrologically determined in this region. The NMDS1 gradient is corroborated by PERMANOVA (pseudo-F = 17.03, p = 0.001) and CCA (both constrained on the same environmental matrix) — the compositional differentiation is not an ordination artefact.

**¶3 — Indicator species confirm discrete zonation**
High IndVal scores for conifers (*Pinus roxburghii* 0.794, *Picea spinulosa* 0.463, *Pinus wallichiana* 0.411, *Abies densa* 0.387) confirm strong habitat fidelity and discrete boundaries. Lower IndVal in broadleaf types reflects wider environmental tolerances and greater species turnover. Rhododendron species as alpine indicators (*R. anthopogon*, *R. aeruginosum*, *R. setosum*) are consistent with their known dominance above treeline.

**¶4 — Network modularity mirrors vertical zonation**
Three co-occurrence modules correspond spatially to recognisable vegetation belts. Hub species — *Maesa chisia*, *Ficus* spp., *Acer campbellii* — are structurally central in the network, representing candidate umbrella or foundation species for conservation prioritisation.

**¶5 — SCI gradient reflects succession stage and disturbance**
The SCI gradient (subtropical > warm broadleaved > cool broadleaved > ... > alpine scrub) is partly a function of inherent climatic limitations (fewer growing-degree-days at altitude) and partly of human disturbance history. Low SCI in Non Forest (−3.13) and Chirpine Forest (−3.01) merits investigation as potential degradation indicators.

**¶6 — Spatially-explicit greening: patterns and drivers**
The finding that 42.9% of Bhutan's forested area is significantly greening is consistent with the "global greening" phenomenon documented from MODIS (Zhu et al. 2016) and with specific Himalayan studies reporting enhanced vegetation productivity across Nepal and NE India (Lamsal et al. 2017). The elevation gradient in greening intensity — strongest at low elevations (< 1,500 m), weakest in the montane zone (2,000–4,000 m), with a secondary peak at > 4,000 m — suggests multiple co-occurring drivers. Low-elevation greening may reflect community forestry programmes and reduced disturbance pressure. The high-elevation signal (alpine scrub: 43.8% significant greening) is consistent with climate warming-driven upslope shrubification documented elsewhere in the Hindu Kush Himalaya. The mid-elevation trough warrants investigation as potentially linked to increased monsoon variability or anthropogenic disturbance in the most densely populated elevation bands. The positive richness–EVI slope correlation (r = 0.105, p < 0.001) is consistent with the productivity-diversity hypothesis and suggests that areas with higher plant diversity are also those experiencing stronger positive vegetation trends — though causality cannot be established from a single-epoch cross-sectional design.

**¶7 — Limitations**
- The sklearn MDS `stress_` value (0.338) is a raw residual, not Kruskal's normalized stress-1 — the standard "< 0.20 poor, > 0.30 misleading" thresholds do not apply; for submission, replace sklearn MDS with vegan `metaMDS` (999 starts) to report proper stress-1; compositional patterns are independently supported by PERMANOVA (pseudo-F = 17.03, p = 0.001)
- Pixel-level EVI classifications use a normal approximation for MK p-values (where GEE-exported p-value band was unavailable); analytical p-values are standard but introduce minor approximation error for short time series
- NFI is a single-epoch survey; temporal diversity dynamics require repeat inventory
- Co-occurrence edges are all positive (co-presence counts); null-model-based competitive exclusion detection is needed for a complete assembly picture
- CCA1 axis explained negligible variance; only CCA2 is ecologically interpretable
- EVI spatial resolution (~250 m MODIS) may not capture fine-scale within-plot variation in forest structure; higher-resolution Sentinel-2 integration is recommended for future NFI cycles

**¶8 — Management and policy implications**
- Subtropical and warm broadleaved forests (highest richness, highest SCI) warrant highest biodiversity protection priority
- Cold-season temperature thresholds define ecologically critical transition zones vulnerable to warming
- SCI proposed as a standardised structural metric for future NFI cycles
- The 24-year greening trend validates Bhutan's conservation model but monitoring should disaggregate to forest-type and elevation levels

---

## 5. Conclusions (~180 words)

Bhutan's forests display strong vertical zonation structured primarily by cold-season temperature, with species richness declining 2.8× from the subtropical lowlands to the alpine zone. NMDS and CCA confirm that community composition shifts predictably along a temperature-seasonality gradient, while 410 significant indicator species associations validate discrete phytogeographic boundaries. Co-occurrence network analysis reveals modular community structure consistent with three major vegetation belts, and betweenness-central hub species represent conservation priority candidates. The Stratification Complexity Index captures multi-layer structural differences, with subtropical and warm broadleaved forests being structurally most complex. Pixel-level MODIS EVI trend analysis (2000–2024) confirms that 42.9% of Bhutan's forest area is significantly greening, with the signal strongest at low elevations (< 1,500 m: > 57% significantly greening) and weakest in the montane zone; a secondary greening peak at > 4,000 m is consistent with high-elevation shrubification. EVI slope correlates positively with species richness (r = 0.105, p < 0.001), linking vegetation productivity trends to biodiversity patterns. Together, these results provide the first integrated, country-scale quantitative baseline for Bhutan's forest stratification and establish a reproducible open-source framework for long-term biodiversity and ecosystem monitoring.

---

## Figures

| # | Title | Source file | Notes |
|---|---|---|---|
| 1 | Study area and NFI plot distribution | `map_species_richness.png` (adapted) | Bhutan territory fill + boundary; 1,942 plots coloured by forest type; YlGn colormap; publication-quality (module 10) |
| 2 | Alpha diversity across the elevational gradient | Computed from alpha table | Richness, Shannon H, layer richness vs. elevation; LOESS + 95% CI |
| 3 | NMDS ordination of forest community composition | Beta diversity outputs | 2D biplot; forest types as coloured hulls; env vectors overlaid; stress = 0.338 reported |
| 4 | CCA triplot: species, sites, and environmental vectors | CCA tables | Sites (grey), species (blue), env arrows (red); CCA2 axis labelled |
| 5 | Species co-occurrence network | Network edges + node metrics | Nodes coloured by module (3 modules); size ∝ degree; hub species labelled |
| 6 | Stratification Complexity Index: spatial and elevational | `map_sci_index.png` + SCI table | (a) spatial scatter map — RdYlGn diverging, centred at 0; (b) SCI vs. elevation scatter by forest type |
| 7 | EVI spatial trend map 2000–2024 | `evi_spatial_trend_map.png` | Pixel-level classification (250 m): green = sig. greening, brown = sig. browning, grey = stable; Bhutan territory fill + boundary + white-ring NFI dots; Mann-Kendall p ≤ 0.05 |
| 8 | EVI trend slope by elevation and forest type | `evi_slope_vs_elevation.png` + `evi_slope_by_forest_type.png` | (a) per-plot Theil-Sen slope vs. elevation scatter with rolling mean ± SE ribbon, elevation zone bands; (b) horizontal box plots sorted by median slope, n-counts annotated |
| 9 | EVI slope vs. species richness and SCI | `evi_slope_vs_richness_sci.png` | 2-panel scatter: per-plot slope (y) vs. richness / SCI (x); OLS regression + bootstrap 95% CI band; coloured by elevation (terrain_r); Pearson r = 0.105, p < 0.001 |
| S1 | NMDS1 scores spatial map | `map_nmds1_scores.png` | Spatial gradient of NMDS1 across Bhutan; PuOr diverging colormap centred at 0 |
| S2 | Full indicator species table | indicator_species_detailed.csv | All 410 significant indicators, IndVal, p-value, forest zone |
| S3 | Alpha diversity by dzongkhag and forest type | Alpha table | Box plots; districts + 12 forest types |
| S4 | Integrated EVI panel | `evi_integrated_panel.png` | 4-panel: (a) pixel spatial map + (b) elevation band bar chart ± 95% CI + (c) forest type box plots + (d) richness scatter |
| S5 | NFI plot EVI trend classification map | `map_evi_trends.png` | Per-plot scatter: Greening / Browning / Stable (Greening plotted on top); genuine spatial variation from raster extraction; Bhutan fill + boundary (module 10) |

---

## Tables

| # | Title | Content |
|---|---|---|
| 1 | Alpha diversity summary by forest type | N plots, mean richness, Shannon H, Simpson D (±SD), layer richness |
| 2 | Top indicator species per forest zone | Species, zone, IndVal, p-value — 3 per zone across 12 zones |
| 3 | CCA environmental biplot scores | Variable, CCA1, CCA2, magnitude — ranked by ecological importance |
| 4 | EVI trend area classification | Trend class, n pixels, area km², % valid area (sig greening / browning / stable) |

---

## Word Budget

| Section | Target words |
|---|---|
| Abstract | 250 |
| Introduction | 900 |
| Methods | 1,400 |
| Results | 1,500 |
| Discussion | 1,200 |
| Conclusions | 180 |
| Captions + tables | 600 |
| **Total** | **~6,030** |

---

## Key Numbers Reference

| Metric | Value |
|---|---|
| NFI plots | 1,942 |
| Elevation range | 113–5,469 m (mean 2,454 ± 1,271 m) |
| Forest types | 12 |
| Mean species richness | 17.1 ± 9.1 spp/plot (range 1–57) |
| Peak richness band | 500–1,000 m (24.8 ± 9.0) |
| Lowest richness band | >4,000 m (8.9 ± 5.6) |
| Mean Shannon H | 1.905 ± 0.661 |
| Mean Simpson D | 0.740 ± 0.190 |
| Tree layer richness | 9.1 ± 7.3 |
| Shrub layer richness | 5.5 ± 4.2 |
| Herb layer richness | 2.8 ± 3.2 |
| sklearn MDS `stress_` (2D) | 0.338 — raw residual metric; NOT Kruskal stress-1; standard thresholds do not apply |
| PERMANOVA pseudo-F | **17.03**, p = 0.001 (999 permutations) — forest types compositionally distinct |
| Action required | Replace sklearn MDS → vegan `metaMDS` (999 starts) to report proper Kruskal stress-1 |
| NMDS1 range | −1.065 to +0.968 |
| Primary CCA driver | bio11 (CCA2 = +0.610) |
| Significant indicator associations | 410 (all p ≤ 0.05) |
| Strongest IndVal | *Pinus roxburghii* = 0.794 |
| Network nodes (species) | 1,115 |
| Network edges | 29,854 |
| Network communities | 3 (523 / 461 / 131 species) |
| SCI range | −15.15 to +25.15 |
| Highest SCI forest type | Subtropical Forest (+4.49) |
| Lowest SCI forest type | Dry Alpine Scrub (−5.44) |
| EVI data | MODIS MOD13Q1 V061, 2000–2024, **~250 m** native resolution |
| Total valid EVI pixels | 684,055 pixels (42,754 km²) |
| Significantly greening (p ≤ 0.05) | 293,521 pixels — 18,345 km² — **42.9%** |
| Significantly browning (p ≤ 0.05) | 8,900 pixels — 556 km² — 1.3% |
| Stable / non-significant | 381,634 pixels — 23,852 km² — 55.8% |
| Peak greening elevation | 500–1,000 m (mean slope 0.00164 EVI yr⁻¹; 61.8% sig greening) |
| Weakest greening elevation | 3,500–4,000 m (mean slope 0.00063; 19.6% sig greening) |
| Most greening forest type | Dry Alpine Scrub (94.3%), Subtropical Forest (94.2%), Warm Broadleaved (94.1%) |
| Least greening forest type | Spruce Forest (57.1%), Blue Pine Forest (63.0%) |
| EVI slope vs richness | Pearson r = 0.105, p < 0.001 (n = 1,910 plots) |

---

## Pipeline Status (as of 2026-02-18)

| Module | Status | Key outputs |
|--------|--------|-------------|
| 00–03 | ✅ Complete | data inspection, cleaning, env extraction, alpha diversity |
| 04 beta_diversity | ✅ Complete (20 min) | NMDS scores, stress = 0.338 |
| 05 cca_ordination | ✅ Complete | CCA triplot, biplot scores |
| 06 indicator_species | ✅ Complete | 410 significant IndVal associations |
| 07 co_occurrence | ✅ Complete | 1,115 nodes, 29,854 edges, 3 modules |
| 08 evi_spatial_analysis | ✅ Complete (34 s) | 5 plots + 4 tables in `outputs/evi_spatial/` |
| 09 sci_index | ✅ Complete | SCI per plot, forest type summaries |
| 10 spatial_mapping | ✅ Complete (13 s) | 4 publication-quality maps in `outputs/spatial_maps/` |
| 11 reporting | ⬜ Not yet run | HTML pipeline report |

**All figures for Figs. 7–9 + S4–S5 confirmed production quality** (18:22, 2026-02-18)

---

## Immediate Next Steps

### Before writing
1. ⚠️ **Replace sklearn MDS → vegan `metaMDS`** — the current implementation (sklearn, 4 random starts) is not publication-standard for ecology; use R's vegan `metaMDS(bray, k=2, trymax=100)` to get proper Kruskal stress-1 and convergence; PERMANOVA (F=17.03, p=0.001) already confirms the compositional signal is real
2. Draft **Table 1** (alpha diversity by forest type) — all numbers in §3.1
3. Draft **Table 2** (indicator species) — top 3 per forest zone, all 36 rows ready in §3.4
4. Draft **Table 4** (EVI area classification) — copy directly from `outputs/evi_spatial/tables/evi_area_stats.csv`

### Writing order (recommended)
5. Write **§2 Methods** first (most objective) — §2.1 → §2.4 → §2.10 → §2.5–§2.9 → §2.11
6. Write **§3 Results** — populate table cells, insert figure cross-references
7. Write **§4 Discussion** — use paragraph outlines above, ≤1,200 words
8. Write **§1 Introduction** last — 900 words, 5 paragraphs
9. Write **Abstract** from the "Key Numbers Reference" table above

### Editorial and submission
10. Review *Forest Ecology and Management* author guidelines (PDF in this folder)
11. Confirm journal word limit (8,000 words) and figure number limit
12. Decide corresponding author and institutional affiliations before submission
13. Obtain DOIs or preprint links for all data and code cited in §2.11

### Optional improvements (pre-submission)
14. Re-run module 11 to generate the HTML pipeline summary report
15. Consider adding a 5th figure: SCI spatial map (`map_sci_index.png`) with elevation profile subplot — currently Fig. 6 composite
