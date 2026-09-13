"""Traceable, independently reopenable exports from saved numerical products."""

import csv
import html
import json
import re
import zipfile
from pathlib import Path

import fiona
import netCDF4
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from rasterio.transform import from_origin

EXPORT_FORMATS = {"geotiff", "kml", "geojson", "shapefile", "csv", "html"}
FIELD_MAP = {
    "cell": "cell_id",
    "maximum_depth_m": "max_depth",
    "maximum_velocity_m_s": "max_vel_ms",
    "flood_duration_s": "duration_s",
    "arrival_elapsed_s": "arrival_s",
    "cell_state": "state",
}


def safe_name(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    if not result:
        raise ValueError("Export filename is empty after sanitization")
    return result[:80]


def _read(source: Path, product: Path):
    with netCDF4.Dataset(source) as raw, netCDF4.Dataset(product) as derived:
        provenance = json.loads(raw.provenance_json)
        crs_value = provenance.get("crs")
        if not crs_value:
            raise ValueError("Saved result has no CRS; export is unavailable")
        try:
            crs = CRS.from_user_input(crs_value)
        except Exception as exc:
            raise ValueError(f"Saved result CRS is not exportable: {crs_value}") from exc
        x = np.asarray(derived["x"][:], dtype=float)
        y = np.asarray(derived["y"][:], dtype=float)
        area = np.asarray(derived["cell_area"][:], dtype=float)
        values = {name: np.ma.asarray(derived[name][:]).filled(np.nan) for name in FIELD_MAP if name != "cell"}
        state = np.asarray(derived["cell_state"][:], dtype=np.int16)
        times = np.asarray(raw["time"][:], dtype=float)
        return crs, x, y, area, values, state, times, provenance


def _features(x, y, area, values, state):
    for index, (px, py) in enumerate(zip(x, y)):
        yield {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(px), float(py)]},
            "properties": {
                "cell_id": int(index),
                "maximum_depth_m": None if not np.isfinite(values["maximum_depth_m"][index]) else float(values["maximum_depth_m"][index]),
                "maximum_velocity_m_s": None if not np.isfinite(values["maximum_velocity_m_s"][index]) else float(values["maximum_velocity_m_s"][index]),
                "flood_duration_s": None if not np.isfinite(values["flood_duration_s"][index]) else float(values["flood_duration_s"][index]),
                "arrival_elapsed_s": None if not np.isfinite(values["arrival_elapsed_s"][index]) else float(values["arrival_elapsed_s"][index]),
                "cell_state": int(state[index]),
                "cell_area_m2": float(area[index]),
            },
        }


def _write_geotiff(path, crs, x, y, values, metadata):
    if len(x) == 0:
        raise ValueError("Saved result contains no cells")
    dx = float(np.median(np.diff(np.sort(x)))) if len(x) > 1 and np.any(np.diff(np.sort(x)) > 0) else 1.0
    dy = float(np.median(np.diff(np.sort(y)))) if len(y) > 1 and np.any(np.diff(np.sort(y)) > 0) else 1.0
    transform = from_origin(float(np.min(x)) - dx / 2, float(np.max(y)) + dy / 2, dx, dy)
    array = np.asarray(values["maximum_depth_m"], dtype="float32")[np.newaxis, :]
    with rasterio.open(path, "w", driver="GTiff", height=1, width=len(x), count=1, dtype="float32",
                       crs=crs, transform=transform, nodata=-9999.0) as dst:
        dst.write(np.where(np.isfinite(array), array, -9999.0), 1)
        dst.update_tags(damsafe_units="metres", coordinate_convention="cell-centre strip",
                        nodata="-9999", source_crs=crs.to_string(), **{"run_provenance": json.dumps(metadata)})


def _write_geojson(path, crs, x, y, area, values, state):
    body = {"type": "FeatureCollection", "name": "DamSafe numerical cells",
            "crs": {"type": "name", "properties": {"name": crs.to_string()}},
            "coordinate_convention": "Point coordinates are cell centres in the saved result CRS",
            "features": list(_features(x, y, area, values, state))}
    path.write_text(json.dumps(body, indent=2, allow_nan=False), encoding="utf-8")


def _write_kml(path, crs, x, y, area, values, state):
    to_wgs84 = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    placemarks = []
    for feature in _features(x, y, area, values, state):
        lon, lat = to_wgs84.transform(*feature["geometry"]["coordinates"])
        props = feature["properties"]
        description = html.escape("; ".join(f"{key}={value}" for key, value in props.items()))
        placemarks.append(f"<Placemark><name>Cell {props['cell_id']}</name><description>{description}</description>"
                          f"<Point><coordinates>{lon},{lat},0</coordinates></Point></Placemark>")
    path.write_text('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
                    + "".join(placemarks) + "</Document></kml>", encoding="utf-8")


def _write_shapefile(path, crs, x, y, area, values, state):
    folder = path.with_suffix("")
    folder.mkdir()
    schema = {"geometry": "Point", "properties": {
        "cell_id": "int", "max_depth": "float", "max_vel_ms": "float", "duration_s": "float",
        "arrival_s": "float", "state": "int", "area_m2": "float",
    }}
    with fiona.open(folder / "cells.shp", "w", driver="ESRI Shapefile", schema=schema,
                    crs_wkt=crs.to_wkt(), encoding="UTF-8") as dst:
        for feature in _features(x, y, area, values, state):
            p = feature["properties"]
            dst.write({"geometry": feature["geometry"], "properties": {
                "cell_id": p["cell_id"], "max_depth": p["maximum_depth_m"], "max_vel_ms": p["maximum_velocity_m_s"],
                "duration_s": p["flood_duration_s"], "arrival_s": p["arrival_elapsed_s"],
                "state": p["cell_state"], "area_m2": p["cell_area_m2"],
            }})
    (folder / "fields.txt").write_text("Shapefile field mapping: maximum_depth_m -> max_depth; "
                                       "maximum_velocity_m_s -> max_vel_ms; flood_duration_s -> duration_s; "
                                       "arrival_elapsed_s -> arrival_s; cell_state -> state; cell_area_m2 -> area_m2\n",
                                       encoding="utf-8")
    (folder / "cells.cpg").write_text("UTF-8", encoding="ascii")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in folder.iterdir():
            archive.write(item, item.name)


def _write_csv(path, source, x, y, values, state, times):
    with netCDF4.Dataset(source) as raw:
        depth = np.ma.asarray(raw["h"][:]).filled(np.nan)
        wet_threshold = float(raw.wet_threshold_m)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cell_id", "x", "y", "frame", "elapsed_s", "depth_m", "state"])
        for frame, elapsed in enumerate(times):
            for cell in range(len(x)):
                valid = np.isfinite(depth[frame, cell])
                status = "NODATA" if not valid else "WET" if depth[frame, cell] >= wet_threshold else "DRY"
                writer.writerow([cell, x[cell], y[cell], frame, elapsed, None if not valid else depth[frame, cell], status])


def _write_report(path, run_id, metadata, provenance, area):
    path.write_text(f"""<!doctype html><meta charset="utf-8"><title>DamSafe run {html.escape(run_id)}</title>
<h1>DamSafe numerical result report</h1><p><b>Run:</b> {html.escape(run_id)}</p>
<p><b>Evidence:</b> {html.escape(str(metadata.get('evidence_status', 'UNASSESSED')))}</p>
<p><b>Engine:</b> {html.escape(str(provenance.get('engine', {}).get('engine')))}</p>
<p><b>Units:</b> depth metres; velocity metres/second; area square metres; elapsed time seconds.</p>
<p><b>Limitations:</b> saved numerical output is not site validation; coordinate convention and nodata are documented in companion exports.</p>
<pre>{html.escape(json.dumps(area, indent=2))}</pre>""", encoding="utf-8")


def create_export(source: Path, product: Path, output_dir: Path, run_id: str, export_format: str, metadata=None):
    if export_format not in EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format: {export_format}")
    output_dir.mkdir(parents=True, exist_ok=True)
    crs, x, y, area, values, state, times, provenance = _read(source, product)
    stem = safe_name(f"{run_id}-{export_format}")
    path = output_dir / f"{stem}.{'tif' if export_format == 'geotiff' else 'zip' if export_format == 'shapefile' else 'html' if export_format == 'html' else export_format}"
    if export_format == "geotiff":
        _write_geotiff(path, crs, x, y, values, metadata or {})
    elif export_format == "geojson":
        _write_geojson(path, crs, x, y, area, values, state)
    elif export_format == "kml":
        _write_kml(path, crs, x, y, area, values, state)
    elif export_format == "shapefile":
        _write_shapefile(path, crs, x, y, area, values, state)
    elif export_format == "csv":
        _write_csv(path, source, x, y, values, state, times)
    else:
        _write_report(path, run_id, metadata or {}, provenance, {"frames": len(times), "cells": len(x)})
    return path


def verify_export(path: Path, export_format: str):
    if export_format == "geotiff":
        with rasterio.open(path) as src:
            return {"format": export_format, "crs": src.crs.to_string() if src.crs else None,
                    "nodata": src.nodata, "units": src.tags().get("damsafe_units"), "count": src.width}
    if export_format == "geojson":
        body = json.loads(path.read_text(encoding="utf-8"))
        return {"format": export_format, "feature_count": len(body["features"]), "crs": body["crs"]["properties"]["name"]}
    if export_format == "shapefile":
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
        required = {"cells.shp", "cells.shx", "cells.dbf", "cells.prj", "cells.cpg"}
        return {"format": export_format, "complete": required.issubset(names), "components": sorted(names)}
    return {"format": export_format, "bytes": path.stat().st_size}
