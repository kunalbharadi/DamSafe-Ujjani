import json

import netCDF4
import pytest
from damsafe.numerics.geometry import attach_native_polygons


@pytest.mark.parametrize('offset, expected', [(0, True), (10, False)])
def test_native_geometry_requires_matching_cell_identity(tmp_path, offset, expected):
    result = tmp_path / 'normalized.nc'
    with netCDF4.Dataset(result, 'w') as ds:
        ds.createDimension('cell', 1)
        ds.createVariable('x', 'f8', ('cell',))[:] = [1]
        ds.createVariable('y', 'f8', ('cell',))[:] = [1]
        ds.provenance_json = json.dumps({'native_file': 'example_map.nc'})
    native = tmp_path / 'dflowfm' / 'DFM_OUTPUT_example'
    native.mkdir(parents=True)
    with netCDF4.Dataset(native / 'example_map.nc', 'w') as ds:
        ds.createDimension('cell', 1)
        ds.createDimension('vertex', 4)
        ds.createVariable('mesh2d_face_x', 'f8', ('cell',))[:] = [1 + offset]
        ds.createVariable('mesh2d_face_y', 'f8', ('cell',))[:] = [1]
        ds.createVariable('mesh2d_face_x_bnd', 'f8', ('cell', 'vertex'))[:] = [[0, 2, 2, 0]]
        ds.createVariable('mesh2d_face_y_bnd', 'f8', ('cell', 'vertex'))[:] = [[0, 0, 2, 2]]
    cells = [{'cell': 0}]
    attach_native_polygons(result, cells)
    assert ('polygon' in cells[0]) == expected
    if expected:
        assert cells[0]['polygon'] == [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]
