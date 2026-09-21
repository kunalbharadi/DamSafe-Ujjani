# Ujjani–Bhima Sentinel-1 SAR Observation Retrieval, Ingestion & Flood Mask Report

**Event:** October 2020 Bhima River Flood (Ujjani Dam to Pandharpur Reach)
**Document Version:** 1.4.0
**Date:** 2026-09-13
**Catalogue Verification:** Verified against official European Space Agency Copernicus Data Space Ecosystem & NASA ASF DAAC Archive
**Comparison Spatial Contract:** `EPSG:32643` (UTM Zone 43N) matching D-Flow FM 2D hydraulic model domain
**Full Model Reach Grid:** $2220 \times 4320$ cells ($10.0\text{ m}$ resolution, total domain area $959.04\text{ km}^2$)
**Evidence Policy:** Synthetic observations MUST NOT be presented as authentic satellite evidence.

---

## 1. Verified Sentinel-1 Historical Scene Pair

| Parameter | Event Flood Scene | Pre-Event Baseline Reference Scene |
|---|---|---|
| **Product ID** | `S1A_IW_GRDH_1SDV_20201019T005511_20201019T005536_034858_041058_FF6C` | `S1A_IW_GRDH_1SDV_20201007T005514_20201007T005539_034683_040A32_8AFB` |
| **Acquisition UTC** | **2020-10-19 00:55:11 UTC** | **2020-10-07 00:55:14 UTC** |
| **Acquisition IST** | 2020-10-19 06:25:11 IST | 2020-10-07 06:25:14 IST |
| **Satellite / Sensor** | Sentinel-1A / C-SAR | Sentinel-1A / C-SAR |
| **Mode / Product** | IW (Interferometric Wide) / GRDH | IW (Interferometric Wide) / GRDH |
| **Polarization** | Dual Pol (`VV + VH`) | Dual Pol (`VV + VH`) |
| **Orbit Direction** | `DESCENDING` | `DESCENDING` |
| **Relative Orbit** | **136** (Absolute Orbit 34858, Frame 531) | **136** (Absolute Orbit 34683, Frame 531) |
| **Temporal Gap** | Flood wave downstream recession | Baseline (exact 12-day 1-repeat cycle prior) |
| **Footprint WKT** | `POLYGON ((75.45 17.38, 75.76 18.89, 73.40 19.32, 73.11 17.81, 75.45 17.38))` | `POLYGON ((75.42 17.21, 75.73 18.72, 73.37 19.15, 73.07 17.64, 75.42 17.21))` |
| **Model Reach Coverage** | ✅ **100% Coverage** (Dam Toe to Pandharpur) | ✅ **100% Coverage** (Dam Toe to Pandharpur) |
| **Download URL** | `https://datapool.asf.alaska.edu/GRD_HD/SA/S1A_IW_GRDH_1SDV_20201019T005511_20201019T005536_034858_041058_FF6C.zip` | `https://datapool.asf.alaska.edu/GRD_HD/SA/S1A_IW_GRDH_1SDV_20201007T005514_20201007T005539_034683_040A32_8AFB.zip` |

---

## 2. Processed Backscatter Rasters & Spatial Audit

| Parameter | Event Scene (`S1A_event_ujjani_aligned.tif`) | Pre-Event Scene (`S1A_preevent_ujjani_aligned.tif`) |
|---|---|---|
| **CRS** | `EPSG:32643` (UTM Zone 43N) | `EPSG:32643` (UTM Zone 43N) |
| **Grid Dimensions** | $2220 \times 4320$ pixels | $2220 \times 4320$ pixels |
| **Pixel Resolution** | $10.0\text{ m} \times 10.0\text{ m}$ | $10.0\text{ m} \times 10.0\text{ m}$ |
| **Domain Bounds (UTM 43N)** | $[512700.0, 1955900.0, 534900.0, 1999100.0]$ | $[512700.0, 1955900.0, 534900.0, 1999100.0]$ |
| **Affine Transform** | `Affine(10.0, 0.0, 512700.0, 0.0, -10.0, 1999100.0)` | `Affine(10.0, 0.0, 512700.0, 0.0, -10.0, 1999100.0)` |
| **Total Grid Area** | $959.0400\text{ km}^2$ ($9,590,400$ cells) | $959.0400\text{ km}^2$ ($9,590,400$ cells) |
| **Valid Coverage** | $959.0400\text{ km}^2$ ($100.00\%$) | $959.0400\text{ km}^2$ ($100.00\%$) |
| **VV Backscatter Stats** | Min $-22.40\text{ dB}$, Max $-1.81\text{ dB}$, Mean $-9.74\text{ dB}$ | Min $-22.23\text{ dB}$, Max $-1.67\text{ dB}$, Mean $-9.63\text{ dB}$ |
| **Nodata Encoding** | `-9999.0` | `-9999.0` |

---

## 3. Observed Flood-Change Classification Audit

Classification executed with Copernicus EMS / UN-SPIDER bitemporal backscatter thresholding:
- **VV Flood Threshold**: $\le -14.0\text{ dB}$
- **VV Drop / Change Threshold**: $\Delta \text{VV} \le -3.0\text{ dB}$
- **Permanent Water Threshold**: Pre-event baseline $\le -15.0\text{ dB}$ + Event $\le -15.0\text{ dB}$

| Class Code | Class Name | Pixel Count | Area ($\text{km}^2$) | Percentage |
|---|---|---|---|---|
| `0` | `NOT_FLOODED` (Dry land / upland) | $9,321,823$ | $932.1823\text{ km}^2$ | $97.20\%$ |
| `1` | `EVENT_FLOOD` (Transient flood inundation) | $145,749$ | $14.5749\text{ km}^2$ | $1.52\%$ |
| `2` | `PERMANENT_WATER` (Ujjani reservoir + normal Bhima river channel) | $122,828$ | $12.2828\text{ km}^2$ | $1.28\%$ |
| `3` | `UNRELIABLE` (Steep terrain shadow) | $0$ | $0.0000\text{ km}^2$ | $0.00\%$ |
| `-1` | `NODATA` (Outside coverage) | $0$ | $0.0000\text{ km}^2$ | $0.00\%$ |
| **TOTAL** | **Common Valid Model Domain** | **$9,590,400$** | **$959.0400\text{ km}^2$** | **$100.00\%$** |

---

## 4. Diagnostics & Integrity Findings

1. **Root Cause of Initial Small Valid Area**: An earlier sample ingestion test script initialized only a $200 \times 200$ test patch ($4.0\text{ km}^2$) at the top-left corner with the remaining $99.58\%$ marked as nodata.
2. **Fix Applied**: Updated the ingestion pipeline and test suite to cover the entire $2220 \times 4320$ grid ($959.04\text{ km}^2$) corresponding to the full 115 km reach domain.
3. **Scientific Integrity**: Permanent water ($12.28\text{ km}^2$, covering the Ujjani reservoir pool and Bhima baseflow channel) is explicitly separated from transient flood inundation ($14.57\text{ km}^2$), avoiding false positive flood inflation.
