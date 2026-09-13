# Ujjani Dam & Bhima River Reach Site Data Catalogue

**Domain:** Ujjani Dam (Bhima Reservoir) & Bhima River Downstream Reach to Pandharpur
**Bounding Box (WGS84):** `(74.60°E, 17.65°N, 75.95°E, 18.35°N)`
**Projected Coordinate Reference System (CRS):** `EPSG:32643` (WGS 84 / UTM Zone 43N)
**Vertical Datum:** EGM96 Geoid / Orthometric Height above MSL
**Date of Document:** September 2026
**Status:** Real Site Reference & Preprocessing Specification

---

## 1. Primary Site Specification

### 1.1 Dam & Reservoir Engineering Geometry
| Parameter | Value | Units | Source / Reference |
|---|---|---|---|
| **Dam Name** | Ujjani (Bhima Dam) | - | WRD Maharashtra, CWC National Register of Large Dams |
| **Location** | Ujjani, Madha Taluka, Solapur District, Maharashtra | - | `18.0753° N, 75.1197° E` |
| **River Basin** | Bhima River (Krishna Basin) | - | CWC Krishna Basin Organisation |
| **Dam Type** | Composite (Masonry Gravity + Earthfill Flanks) | - | NRLD 2023 |
| **Total Dam Length** | 2,534 | m | WRD Technical Specs |
| **Masonry Spillway Length** | 602 | m | WRD Technical Specs |
| **Maximum Dam Height** | 56.40 | m | Foundation to Crest |
| **Dam Crest Level** | 497.00 | m MSL | Official Gauge Datum |
| **Full Reservoir Level (FRL)** | 496.83 | m MSL | WRD Operating Rules |
| **Maximum Water Level (MWL)** | 497.58 | m MSL | WRD Operating Rules |
| **Minimum Drawdown Level (MDDL)** | 491.03 | m MSL | WRD Operating Rules |
| **Gross Storage Capacity** | 3.140 (117.24 TMC / 3,140 MCM) | km³ / TMC / MCM | CWC Register |
| **Live Storage Capacity** | 1.517 (53.57 TMC / 1,517 MCM) | km³ / TMC / MCM | CWC Register |
| **Dead Storage Capacity** | 1.623 (57.30 TMC / 1,623 MCM) | km³ / TMC / MCM | CWC Register |
| **Reservoir Water Spread Area (FRL)** | 337.0 | km² | CWC Register |
| **Catchment Area** | 14,858 | km² | CWC Register |
| **Spillway Radial Gates** | 41 gates (12.19 m × 8.23 m each) | - | WRD Mechanical Division |
| **Spillway Design Discharge** | 15,700 (~554,000 cusecs) | m³/s | WRD Spillway Design Curve |

### 1.2 Downstream River Reach Geometry (Ujjani Dam to Pandharpur)
| Parameter | Value | Units | Notes |
|---|---|---|---|
| **Reach Length** | 115 | km | Meandering channel distance along Bhima riverbed |
| **Reach Start Point** | `(75.120° E, 18.075° N)` | WGS84 | Spillway stilling basin outlet |
| **Reach End Point** | `(75.335° E, 17.675° N)` | WGS84 | Pandharpur gauging & bridge section |
| **Average Valley Slope** | ~0.00035 (0.35 m/km) | m/m | Derived from GLO-30 DEM along thalweg |
| **Active Channel Width** | 200 – 450 | m | Varies across reaches; identified from Sentinel-2 |
| **Floodplain Width** | 1.5 – 6.0 | km | Inundation extent during >200k cusec events |
| **Dominant Riverbed Material** | Alluvium, silt, sand, basaltic outcrops | - | Field reports & Geological Survey of India |

---

## 2. Dataset Catalogue Matrix

| Dataset Category | Dataset Name / Provider | Spatial Resolution | CRS & Vertical Datum | Temporal Coverage | Licensing / Source URL | Local Ingestion Path / Engine Target | Evidence State |
|---|---|---|---|---|---|---|---|
| **Terrain (DEM)** | Copernicus GLO-30 DEM (ESA / Copernicus Open Access) | 30 m (1 arc-sec) | `EPSG:4326` (reprojected to `EPSG:32643`), EGM96 Geoid | 2020 baseline release | Copernicus Open Licence | GEE: `COPERNICUS/DEM/GLO30` | **VERIFIED_AVAILABLE** (Global coverage, valid bounds) |
| **River Reach Centerline** | HydroRIVERS (WWF / HydroSHEDS v1.0) | Multi-scale vector | `EPSG:4326` (WGS84) | Static | CC-BY 4.0 | Vector GeoJSON / PostGIS | **VERIFIED_AVAILABLE** (Reach ID identified) |
| **Channel Bathymetry** | Riverbed Survey Cross-Sections (WRD Maharashtra) | 500 m station spacing | Local Survey Grid | Pre-monsoon surveys (varies) | Government / Restricted | `site/bathymetry/` | **TERRAIN_APPROXIMATION_ONLY** (Missing sub-surface sounding in open satellite DEM) |
| **Dam & Gate Specifications** | CWC Large Dams Register & WRD Operating Manual | Point / Tabular | N/A | Current | CWC / Open Gov | `backend/damsafe/site/ujjani.py` | **VERIFIED_AUTHORITATIVE** |
| **Stage-Discharge Rating Curves** | Pandharpur Gauge Station (CWC Krishna Division) | Tabular Rating Table | Local Gauge Datum (443.2 m MSL zero) | 2018–2024 annual updates | CWC Gauge Network | `site/rating_curves/pandharpur.csv` | **PARTIAL** (Historical flood peak discharge published; full continuous curve pending CWC release) |
| **Hydrological Inflow & Outflow** | Ujjani Daily Discharge Logs (WRD Pune / Solapur) | Hourly / Daily time-series | N/A | Monsoon 2019, 2020, 2022 | WRD Maharashtra Press Bulletins | `site/events/2020_october_discharge.csv` | **PARTIAL_EVENT_PEAKS** (Hourly hydrograph digitized from district flood bulletin) |
| **Permanent Water Baseline** | JRC Global Surface Water Occurrence v1.4 (EC JRC) | 30 m | `EPSG:4326` | 1984–2021 (38 years) | CC-BY 4.0 | GEE: `JRC/GSW1_4/GlobalSurfaceWater` | **VERIFIED_AVAILABLE** (Occurrence > 80% used as permanent water mask) |
| **Synthetic Aperture Radar (SAR)** | Sentinel-1 Ground Range Detected (GRD) (ESA) | 10 m (IW mode) | `EPSG:4326` Ground Range | 2014–Present (6–12 day revisit) | Copernicus Open Licence | GEE: `COPERNICUS/S1_GRD` | **VERIFIED_AVAILABLE** (Scenes matched for Oct 2020 & Aug 2019) |
| **Downstream Exposure / Infrastructure** | OpenStreetMap (OSM contributors) + WorldPop | Vector (OSM) / 100 m (WorldPop) | `EPSG:4326` / `EPSG:3857` | 2023–2024 | ODbL / CC-BY 4.0 | `backend/damsafe/data/` | **VERIFIED_AVAILABLE** (Solapur, Madha, Pandharpur settlements & bridges) |

---

## 3. Hydrological & Hydraulic Units Preprocessing Standards

### 3.1 Discharge Conversion (Cusecs to SI Units)
In Maharashtra Water Resources Department operations, discharge from Ujjani Dam is officially reported and logged in **cusecs** (cubic feet per second).
DamSafe numerical solvers (e.g. LISFLOOD-FP, Shallow Water 2D solvers) strictly require **m³/s** (SI unit).

$$\text{Discharge } (m^3/s) = \text{Discharge } (\text{cusecs}) \times 0.028316846592$$

$$\text{Discharge } (\text{cusecs}) = \text{Discharge } (m^3/s) \times 35.314666721489$$

### 3.2 Timezone Normalization (IST to UTC)
Dam control room logs and district disaster management bulletins are recorded in **Indian Standard Time (IST, UTC+05:30)**.
Satellite acquisition timestamps (Sentinel-1 SAR) and standard numerical models are referenced to **Universal Time Coordinated (UTC)**.

$$\text{Timestamp}_{\text{UTC}} = \text{Timestamp}_{\text{IST}} - 5\text{ hours } 30\text{ minutes}$$

### 3.3 Coordinate System Projection
- **Source Geometries / Ingestion:** WGS84 Geodetic (`EPSG:4326`) in decimal degrees.
- **Solver Domain Projection:** WGS 84 / UTM Zone 43N (`EPSG:32643`).
- **Domain Extents in UTM Zone 43N:**
  - $X_{\min} \approx 670,000$ m, $X_{\max} \approx 810,000$ m
  - $Y_{\min} \approx 1,950,000$ m, $Y_{\max} \approx 2,030,000$ m
  - Grid resolution: $30.0$ m regular Cartesian grid.

---

## 4. Sub-surface Bathymetry Limitation & Channel Approximation

Satellite DEMs (Copernicus GLO-30, SRTM, ALOS World 3D) capture the water surface elevation at the time of radar/optical acquisition, **not the submerged riverbed thalweg**.

### 4.1 Channel Approximation Rules for Preliminary Testing
When running preliminary exploratory simulations without bathymetric echo-sounding surveys:
1. The domain MUST be flagged as `TERRAIN_APPROXIMATION_ONLY`.
2. A synthetic channel trapezoidal/parabolic incision may be applied along the HydroRIVERS centerline:
   - Approximate bankfull depth: $3.5$ m.
   - Approximate bottom bed width: $120.0$ m.
   - Side slopes: $2:1$ (horizontal:vertical).
   - Manning's $n$ for main channel: $0.035$ (clean, straight, natural stream).
   - Manning's $n$ for floodplain: $0.055$ (agricultural fields with crops/scattered brush).
3. **Scientific Invalidation Warning:** Any model run utilizing this synthetic channel approximation MUST NOT be certified as a validated site run for emergency operational decisions.
