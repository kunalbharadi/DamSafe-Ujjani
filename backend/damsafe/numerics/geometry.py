"""Read native face boundaries only when their cell identity matches the result."""
import json
from pathlib import Path

import netCDF4
import numpy as np


def attach_native_polygons(source: Path, cells: list[dict]) -> None:
    if not cells:
        return
    with netCDF4.Dataset(source) as normalized:
        provenance = json.loads(normalized.provenance_json)
        name = provenance.get("native_file")
        x = np.asarray(normalized["x"][:])
        y = np.asarray(normalized["y"][:])
    if not name or Path(name).name != name:
        return
    candidates = list(source.parent.glob(f"dflowfm/DFM_OUTPUT_*/{name}"))
    if len(candidates) != 1:
        return
    native = candidates[0]
    if not native.resolve().is_relative_to(source.parent.resolve()):
        return
    with netCDF4.Dataset(native) as ds:
        required = ("mesh2d_face_x", "mesh2d_face_y", "mesh2d_face_x_bnd", "mesh2d_face_y_bnd")
        if any(key not in ds.variables for key in required):
            return
        if ds[required[0]].shape != x.shape or ds[required[1]].shape != y.shape:
            return
        if not (np.allclose(ds[required[0]][:], x, rtol=0, atol=1e-6)
                and np.allclose(ds[required[1]][:], y, rtol=0, atol=1e-6)):
            return
        for cell in cells:
            index = cell["cell"]
            xs = np.ma.asarray(ds[required[2]][index]).compressed()
            ys = np.ma.asarray(ds[required[3]][index]).compressed()
            if len(xs) != len(ys) or len(xs) < 3 or not np.all(np.isfinite([xs, ys])):
                continue
            ring = [[float(a), float(b)] for a, b in zip(xs, ys)]
            if ring[-1] != ring[0]:
                ring.append(ring[0])
            cell["polygon"] = ring
            cell["geometry_source"] = "native solver face boundaries; centre identity checked"
