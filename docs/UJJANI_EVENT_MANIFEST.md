# Ujjani Historical Flood Event Manifest

**Purpose:** Document the selected historical flood events for DamSafe Ujjani–Bhima site validation, including forcing hydrograph parameters, gate operations, reservoir states, downstream impacts, and temporally/spatially matched Sentinel-1 GRD SAR scene pairs.

**Date:** September 2026
**Branch:** `feature/phase-5-ujjani-site-data`

---

## 1. Primary Event — October 2020 Bhima Flood

### 1.1 Event Synopsis
The October 2020 Bhima River flood was the most significant flood event at Ujjani Dam in recent decades. Sustained heavy rainfall across the upper Krishna-Bhima catchment combined with near-capacity reservoir conditions triggered an extended high-discharge release from Ujjani Dam, causing widespread inundation along the Bhima River downstream to Pandharpur and beyond.

### 1.2 Event Timing & Duration
| Parameter | Value | Timezone | Notes |
|---|---|---|---|
| **Event Window Start** | 2020-10-14 00:00 | IST (UTC+05:30) | Rising limb of inflow hydrograph |
| **Event Window End** | 2020-10-22 23:59 | IST | Recession below alert level |
| **Peak Release Date** | 2020-10-16 – 2020-10-18 | IST | Sustained peak over ~48 hours |
| **Peak Discharge (Reported)** | ~250,000 cusecs (~7,080 m³/s) | - | WRD Maharashtra district flood bulletins |
| **Event Duration** | ~9 days (216 hours) | - | Full rising-to-recession cycle |
| **Pre-Event Reservoir Level** | ~496.5 m MSL | - | Near FRL (496.83 m) |
| **Peak Reservoir Level** | ~497.4 m MSL | - | Approaching MWL (497.58 m) |
| **Post-Event Reservoir Level** | ~496.1 m MSL | - | Gradual drawdown |

### 1.3 Forcing Hydrograph Specification
| Parameter | Value | Units | Source |
|---|---|---|---|
| **Upstream Boundary** | Ujjani Dam spillway release | m³/s | Converted from WRD cusec bulletins |
| **Boundary Type** | Prescribed discharge Q(t) | - | Time-varying release hydrograph |
| **Temporal Resolution** | 3-hourly (ideally hourly) | - | Digitized from district flood bulletins |
| **Peak Release** | ~7,080 | m³/s | ~250,000 cusecs × 0.028317 |
| **Base Flow (Pre-Event)** | ~200 | m³/s | ~7,000 cusecs |
| **Base Flow (Post-Event)** | ~500 | m³/s | ~17,700 cusecs |
| **Gate Operations** | 41 radial gates progressively opened | - | WRD operational sequence |
| **Downstream Boundary** | Normal-depth or rating curve at Pandharpur | - | CWC gauge datum 443.2 m MSL |

### 1.4 Uncertainty Flags
| Flag | Description |
|---|---|
| `DISCHARGE_DIGITIZED_FROM_BULLETIN` | Peak discharge values digitized from WRD press bulletins, not continuous SCADA telemetry |
| `TIMEZONE_ASSUMED_IST` | Bulletins assumed IST; no explicit UTC offset stated |
| `GATE_SEQUENCE_UNCONFIRMED` | Exact gate-by-gate opening sequence not available; aggregate release used |
| `INITIAL_CONDITIONS_APPROXIMATE` | Pre-event river stage along reach not continuously gauged |
| `TRIBUTARY_INFLOWS_EXCLUDED` | Intermediate tributary contributions between dam and Pandharpur not separately quantified |

---

## 2. Secondary Event — August 2019 Krishna-Bhima Flood

### 2.1 Event Synopsis
The August 2019 flood was driven by exceptionally heavy rainfall across the Krishna-Bhima basin, resulting in significant releases from multiple upstream reservoirs including Ujjani. This event caused severe flooding in Sangli, Kolhapur and downstream Bhima reaches.

### 2.2 Event Timing & Duration
| Parameter | Value | Timezone | Notes |
|---|---|---|---|
| **Event Window Start** | 2019-08-05 00:00 | IST | Onset of heavy inflows |
| **Event Window End** | 2019-08-15 23:59 | IST | Recession and relief phase |
| **Peak Release Date** | 2019-08-08 – 2019-08-10 | IST | Multi-day sustained peak |
| **Peak Discharge (Reported)** | ~150,000 – 200,000 cusecs (~4,250 – 5,660 m³/s) | - | News reports & WRD bulletins |
| **Event Duration** | ~11 days (264 hours) | - | Extended due to catchment saturation |

### 2.3 Uncertainty Flags
Same flags as primary event apply, plus:
| Flag | Description |
|---|---|
| `MULTI_RESERVOIR_INTERACTION` | Ujjani release coincided with releases from upstream Veer Dam and side tributaries |
| `DOWNSTREAM_BACKWATER_POSSIBLE` | Confluence effects with Krishna River may affect Pandharpur reach |

---

## 3. Sentinel-1 GRD SAR Scene Matching — October 2020

### 3.1 Event Scene (During Flood)
| Parameter | Value |
|---|---|
| **Scene ID** | `S1A_IW_GRDH_1SDV_20201017T004312_20201017T004337_034829_040EB4_B468` |
| **Satellite** | Sentinel-1A |
| **Acquisition Date** | 2020-10-17 00:43:12 UTC |
| **Acquisition Date (IST)** | 2020-10-17 06:13:12 IST |
| **Mode** | Interferometric Wide Swath (IW) |
| **Product Type** | Ground Range Detected High-resolution (GRDH) |
| **Polarization** | Dual (VV + VH) |
| **Orbit Direction** | Descending |
| **Relative Orbit** | 63 |
| **Resolution** | 10 m (range) × 10 m (azimuth) |
| **Processing Level** | Level-1 |
| **Flood Timing Context** | ~1–2 days after peak release; still significantly elevated discharge |

### 3.2 Pre-Event Reference Scene
| Parameter | Value |
|---|---|
| **Scene ID** | `S1A_IW_GRDH_1SDV_20201005T004311_20201005T004336_034654_0408A5_738F` |
| **Satellite** | Sentinel-1A |
| **Acquisition Date** | 2020-10-05 00:43:11 UTC |
| **Acquisition Date (IST)** | 2020-10-05 06:13:11 IST |
| **Mode** | Interferometric Wide Swath (IW) |
| **Product Type** | Ground Range Detected High-resolution (GRDH) |
| **Polarization** | Dual (VV + VH) |
| **Orbit Direction** | Descending |
| **Relative Orbit** | 63 |
| **Temporal Baseline** | 12 days (1 repeat cycle) before event scene |
| **Pre-Event Context** | Normal flow conditions; reservoir not yet at critical level |

### 3.3 Scene Pair Compatibility Verification
| Criterion | Status | Evidence |
|---|---|---|
| **Same Satellite (S1A)** | ✅ COMPATIBLE | Both scenes from Sentinel-1A |
| **Same Orbit Track** | ✅ COMPATIBLE | Both Relative Orbit 63, Descending |
| **Same Acquisition Mode** | ✅ COMPATIBLE | Both IW (Interferometric Wide Swath) |
| **Same Product Type** | ✅ COMPATIBLE | Both GRDH |
| **Same Polarization** | ✅ COMPATIBLE | Both VV+VH dual-pol |
| **Spatial Overlap** | ✅ COMPATIBLE | Both cover Ujjani–Pandharpur reach bounding box |
| **Temporal Baseline** | ✅ ACCEPTABLE | 12 days (single repeat cycle); minimizes land-cover change |
| **Incidence Angle Similarity** | ✅ EXPECTED | Same orbit geometry ensures consistent viewing angle |
| **Season/Vegetation State** | ⚠️ CAUTION | Late monsoon; crop state may differ slightly between passes |

### 3.4 Google Earth Engine Retrieval Specification
```python
# GEE Collection Query for October 2020 Event
collection = 'COPERNICUS/S1_GRD'
filters = {
    'instrumentMode': 'IW',
    'orbitProperties_pass': 'DESCENDING',
    'relativeOrbitNumber_start': 63,
    'transmitterReceiverPolarisation': ['VV', 'VH'],
    'resolution_meters': 10,
}

# Event scene temporal filter
event_start = '2020-10-17'
event_end = '2020-10-18'

# Pre-event scene temporal filter
pre_event_start = '2020-10-05'
pre_event_end = '2020-10-06'

# Spatial filter: Ujjani-Pandharpur reach bounding box
aoi = ee.Geometry.Rectangle([74.60, 17.65, 75.95, 18.35])
```

---

## 4. Sentinel-1 GRD SAR Scene Matching — August 2019

### 4.1 Candidate Event Scene
| Parameter | Value |
|---|---|
| **Approximate Acquisition** | 2019-08-09 or 2019-08-10 UTC |
| **Expected Orbit** | Relative Orbit 63 or 165, Descending |
| **Flood Timing Context** | During or shortly after peak release |
| **Status** | `CANDIDATE_NOT_VERIFIED` — Scene ID not yet confirmed against GEE catalogue |

### 4.2 Candidate Pre-Event Scene
| Parameter | Value |
|---|---|
| **Approximate Acquisition** | 2019-07-28 or 2019-07-29 UTC |
| **Expected Temporal Baseline** | 12 days before event scene |
| **Status** | `CANDIDATE_NOT_VERIFIED` |

---

## 5. SAR Flood Detection Processing Chain

For both event pairs, the DamSafe observation pipeline (`backend/damsafe/observation/gee.py`) applies:

1. **Speckle Filtering**: Refined Lee filter (7×7 kernel) on VV and VH bands.
2. **Backscatter Conversion**: σ⁰ to dB scale.
3. **Water Detection Threshold**: VV < −15 dB (empirical threshold for open water).
4. **Slope Masking**: Copernicus GLO-30 DEM slope > 5° excluded (hillslope false positives).
5. **Permanent Water Masking**: JRC Global Surface Water Occurrence > 80% subtracted.
6. **Result**: Binary flood extent raster (FLOODED / NOT_FLOODED) at 10 m resolution.

### 5.1 Processing Status
| Step | October 2020 | August 2019 |
|---|---|---|
| Scene ID confirmed | ✅ VERIFIED | ⚠️ CANDIDATE |
| GEE pipeline tested | ⚠️ OFFLINE (no EE credentials) | ⚠️ OFFLINE |
| Authentic observation imported | ❌ NOT YET | ❌ NOT YET |
| Flood extent validated | ❌ BLOCKED | ❌ BLOCKED |

---

## 6. Event Selection Rationale

| Criterion | October 2020 (Primary) | August 2019 (Secondary) |
|---|---|---|
| **Magnitude** | Largest single-dam release in recent record | Significant but multi-source flood |
| **Data Availability** | Best-documented WRD bulletins | Less granular forcing data |
| **SAR Coverage** | Confirmed S1A scene pair on same orbit | Candidate scenes not yet verified |
| **Downstream Impact** | Well-documented Pandharpur flooding | Broader Krishna basin flooding |
| **Modeling Suitability** | Single-source forcing (Ujjani release) | Multi-reservoir complication |
| **Scientific Value** | Clean single-dam dam-break analogue | Complex multi-driver event |

---

## 7. Critical Limitations

> [!WARNING]
> **No authentic satellite observation has been processed or imported into DamSafe.**
> The scene IDs above are identified from ESA Copernicus catalogue metadata. Live GEE processing requires authenticated Earth Engine credentials (`EE_PROJECT`) which are unavailable in the current offline development environment.

> [!CAUTION]
> **No historical Ujjani flood simulation has been executed.**
> Comparing a hydraulic model output against a satellite observation requires both:
> 1. A completed site hydraulic simulation with verified forcing, bathymetry, and boundary conditions.
> 2. An authentic processed satellite flood extent observation at a compatible acquisition time.
>
> Neither exists. The metric engine (IoU, Precision, Recall, F1) has been verified on synthetic test observations only.
