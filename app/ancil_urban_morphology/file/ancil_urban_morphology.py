#!/usr/bin/env python
"""
Urban morphology application
****************************

Derive the UCLEM urban morphology ancillary fields (STASH items 920-931) from
a set of urban source (e.g. U-Surf) GeoTIFFs, one file per variable, by:

- Reading the first band (the value; later bands are quality flags) of the
  file for each required variable (e.g. HT_ROOF), identified from the file name
  (global_<VARIABLE>_1km_*.tif). Only the part of the source covering the target
  grid is read. Nodata and out of range values are masked.
- Regridding each band to the grid of the provided vegetation fraction
  ancillary. The target grid, land mask and urban mask are all taken from this
  file, so the application is independent of the model resolution.
- Filling urban target points that have no valid regridded value from the
  nearest valid urban point.
- Deriving the UCLEM fields from the bands, setting non-urban land points to 0
  and masking the ocean.

Options:
 * --veg-fraction : The vegetation fraction ancillary (NetCDF) defining the
   target grid, land points and the urban tile (pseudo level 15) fraction.
 * --urban-tile-id : The pseudo level of the urban tile (default 15).
 * --urban-threshold : Urban tile fraction above which a point is urban.
 * --output : the output file
Arguments:
 * The urban source GeoTIFFs follow the options. Files for variables which are
   not needed are ignored.

Example Usage:
ancil_urban_morphology.py --veg-fraction ${veg_frac} --output ${outfile} \
                          ${urban_source_dir}/global_*_1km_*.tif
"""

import os
import re
from typing import Callable, NamedTuple

import ants
import ants.io.save as save
import iris
import iris.coord_systems
import iris.coords
import iris.cube
import iris.fileformats.pp
import numpy as np
from osgeo import gdal

iris.FUTURE.save_split_attrs = True

URBAN_TILE_ID = 15
URBAN_THRESHOLD = 1e-12


class SourceBand(NamedTuple):
    """A required urban source variable, and what values are valid."""

    variable: str
    valid_min: float
    valid_max: float


class OutputField(NamedTuple):
    """A UM field to write, and how to derive it from the regridded bands."""

    stash_item: int
    name: str
    derive: Callable


SOURCE_BANDS = (
    SourceBand("HT_ROOF", 0.0, np.inf),
    SourceBand("CANYON_HWR", 0.0, np.inf),
    SourceBand("WTLUNIT_ROOF", 0.0, 1.0),
    SourceBand("WTROAD_PERV", 0.0, 1.0),
    SourceBand("ALB_ROOF", 0.0, 1.0),
    SourceBand("ALB_WALL", 0.0, 1.0),
    SourceBand("ALB_IMPROAD", 0.0, 1.0),
    SourceBand("ALB_PERROAD", 0.0, 1.0),
    SourceBand("EM_ROOF", 0.0, 1.0),
    SourceBand("EM_WALL", 0.0, 1.0),
    SourceBand("EM_IMPROAD", 0.0, 1.0),
    SourceBand("EM_PERROAD", 0.0, 1.0),
)


def _canyon_fraction(bands):
    return 1.0 - bands["WTLUNIT_ROOF"]


def _canyon_vegetation_fraction(bands):
    return bands["WTROAD_PERV"] * _canyon_fraction(bands)


OUTPUT_FIELDS = (
    OutputField(920, "UCLEM_BUILDING_HEIGHT", lambda bands: bands["HT_ROOF"]),
    OutputField(921, "UCLEM_CANYON_HWR", lambda bands: bands["CANYON_HWR"]),
    OutputField(922, "UCLEM_WIDTH_RATIO", _canyon_fraction),
    OutputField(923, "UCLEM_ROOF_ALBEDO", lambda bands: bands["ALB_ROOF"]),
    OutputField(924, "UCLEM_WALL_ALBEDO", lambda bands: bands["ALB_WALL"]),
    OutputField(925, "UCLEM_ROAD_ALBEDO", lambda bands: bands["ALB_IMPROAD"]),
    OutputField(926, "UCLEM_CANYON_VEG_FRACTION", _canyon_vegetation_fraction),
    OutputField(927, "UCLEM_CANYON_VEG_ALBEDO", lambda bands: bands["ALB_PERROAD"]),
    OutputField(928, "UCLEM_ROOF_EMISSIVITY", lambda bands: bands["EM_ROOF"]),
    OutputField(929, "UCLEM_WALL_EMISSIVITY", lambda bands: bands["EM_WALL"]),
    OutputField(930, "UCLEM_ROAD_EMISSIVITY", lambda bands: bands["EM_IMPROAD"]),
    OutputField(931, "UCLEM_CANYON_VEG_EMISSIVITY", lambda bands: bands["EM_PERROAD"]),
)


def _parse_args():
    parser = ants.AntsArgParser(target_lsm=False, target_grid=False)
    parser.add_argument(
        "--veg-fraction",
        type=ants.config.filepath_readable,
        required=True,
        help="Vegetation fraction ancillary defining the target grid and "
        "urban tile",
    )
    parser.add_argument(
        "--urban-tile-id",
        type=int,
        default=URBAN_TILE_ID,
        help="Pseudo level of the urban tile in the vegetation fractions",
    )
    parser.add_argument(
        "--urban-threshold",
        type=float,
        default=URBAN_THRESHOLD,
        help="Urban tile fraction above which a point is considered urban",
    )
    args = parser.parse_args()
    return args


def mask_invalid_values(values, valid_min, valid_max):
    """Mask non-finite values and values outside [valid_min, valid_max]."""
    return np.ma.masked_where(
        ~np.isfinite(values) | (values < valid_min) | (values > valid_max),
        values,
    )


def source_files_by_variable(source_paths):
    """Map each variable to its source file, using the file name
    global_<VARIABLE>_1km_*.tif."""
    pattern = re.compile(r"global_(?P<variable>[A-Z0-9_]+?)_1km_")
    files = {}
    for path in source_paths:
        match = pattern.match(os.path.basename(path))
        if match:
            files[match.group("variable")] = path
    return files


def target_window(geotransform, shape, template, margin_pixels=2):
    """
    Pixel window (x_offset, y_offset, n_columns, n_rows) of a raster covering
    the horizontal extent of the target template. Falls back to all columns
    where the target is global or crosses the raster's longitude seam.
    """
    origin_x, pixel_width, _, origin_y, _, pixel_height = geotransform
    n_rows, n_columns = shape
    latitude_bounds = template.coord("latitude").contiguous_bounds()
    longitude_bounds = template.coord("longitude").contiguous_bounds()

    row_edges = (latitude_bounds.min(), latitude_bounds.max())
    rows = sorted((edge - origin_y) / pixel_height for edge in row_edges)
    y_start = max(int(np.floor(rows[0])) - margin_pixels, 0)
    y_stop = min(int(np.ceil(rows[1])) + margin_pixels, n_rows)

    # Rasters are in [-180, 180), targets may be in [0, 360)
    lon_min = (longitude_bounds.min() + 180.0) % 360.0 - 180.0
    lon_max = lon_min + (longitude_bounds.max() - longitude_bounds.min())
    if lon_max - lon_min >= 359.0 or lon_max > origin_x + pixel_width * n_columns:
        x_start, x_stop = 0, n_columns
    else:
        x_start = max(int(np.floor((lon_min - origin_x) / pixel_width)) - margin_pixels, 0)
        x_stop = min(int(np.ceil((lon_max - origin_x) / pixel_width)) + margin_pixels, n_columns)
    return x_start, y_start, x_stop - x_start, y_stop - y_start


def read_source_variable(path, source_band, template):
    """
    Read the value band of a source GeoTIFF, over the extent of the target
    template, as a cube with invalid values masked and ascending latitude.
    """
    dataset = gdal.Open(str(path))
    geotransform = dataset.GetGeoTransform()
    x_offset, y_offset, n_columns, n_rows = target_window(
        geotransform, (dataset.RasterYSize, dataset.RasterXSize), template
    )
    values = dataset.GetRasterBand(1).ReadAsArray(
        x_offset, y_offset, n_columns, n_rows
    ).astype("float32")
    nodata = dataset.GetRasterBand(1).GetNoDataValue()
    if nodata is not None:
        values[values == nodata] = np.nan

    origin_x, pixel_width, _, origin_y, _, pixel_height = geotransform
    # North-up rasters have a negative pixel height; we want ascending latitude
    latitudes = origin_y + pixel_height * (y_offset + np.arange(n_rows) + 0.5)
    longitudes = origin_x + pixel_width * (x_offset + np.arange(n_columns) + 0.5)
    if latitudes[0] > latitudes[-1]:
        latitudes = latitudes[::-1]
        values = values[::-1, :]

    coord_system = iris.coord_systems.GeogCS(6371229.0)
    latitude = iris.coords.DimCoord(
        latitudes, "latitude", units="degrees", coord_system=coord_system
    )
    longitude = iris.coords.DimCoord(
        longitudes,
        "longitude",
        units="degrees",
        coord_system=coord_system,
        circular=bool(np.isclose(pixel_width * n_columns, 360.0, atol=0.1)),
    )
    latitude.guess_bounds()
    longitude.guess_bounds()

    return iris.cube.Cube(
        mask_invalid_values(values, source_band.valid_min, source_band.valid_max),
        long_name=source_band.variable,
        units="1",
        dim_coords_and_dims=[(latitude, 0), (longitude, 1)],
    )


def load_target_grid(veg_fraction_path, urban_tile_id, urban_threshold):
    """
    Load the target grid, land mask and urban mask from the vegetation
    fractions. Returns a template cube (2D, on the target grid) along with
    boolean land and urban arrays.
    """
    veg_fraction = ants.load_cube(veg_fraction_path, "vegetation_area_fraction")
    urban_fraction = veg_fraction.extract(
        iris.Constraint(pseudo_level=urban_tile_id)
    )
    if urban_fraction is None:
        raise ValueError(
            f"No pseudo level {urban_tile_id} (urban tile) in {veg_fraction_path}"
        )

    land_mask = ~np.ma.getmaskarray(urban_fraction.data)
    urban_mask = land_mask & (urban_fraction.data.filled(0.0) > urban_threshold)

    template = urban_fraction.copy(np.zeros(urban_fraction.shape))
    template.remove_coord("pseudo_level")
    return template, land_mask, urban_mask


def regrid_band(band_cube, target_template):
    """Regrid a source band to the target grid with the configured scheme."""
    return band_cube.regrid(target_template, ants.regrid.GeneralRegridScheme())


def fill_invalid_urban_points(regridded_band, urban_mask):
    """
    Fill urban points which have no valid regridded value from the nearest
    valid urban point. Only urban points are used as fill candidates.
    """
    urban_only = regridded_band.copy(
        np.ma.masked_where(~urban_mask | np.ma.getmaskarray(regridded_band.data),
                           regridded_band.data)
    )
    n_missing_urban = int((urban_mask & np.ma.getmaskarray(urban_only.data)).sum())
    if n_missing_urban == 0:
        return urban_only, 0

    target_mask = regridded_band.copy(~urban_mask)
    filler = ants.analysis.KDTreeFill(urban_only, target_mask=target_mask)
    return filler(urban_only), n_missing_urban


def build_output_cube(field, bands, land_mask, urban_mask, template):
    """
    Derive an output field: masked over the ocean, 0 over non-urban land and
    the derived value over urban points.
    """
    derived = field.derive(bands).data
    values = np.where(urban_mask, np.ma.filled(derived, 0.0), 0.0)
    cube = template.copy(np.ma.masked_where(~land_mask, values))
    cube.rename(field.name)
    cube.units = "1"
    cube.attributes = {"STASH": iris.fileformats.pp.STASH(1, 0, field.stash_item)}
    return cube


def main(source_paths, veg_fraction_path, urban_tile_id, urban_threshold, outfile, netcdf_only):
    "main top/level"
    gdal.UseExceptions()
    template, land_mask, urban_mask = load_target_grid(
        veg_fraction_path, urban_tile_id, urban_threshold
    )
    print(f"Land points: {land_mask.sum()}, urban points: {urban_mask.sum()}")
    if not urban_mask.any():
        raise ValueError(
            f"No urban points (pseudo level {urban_tile_id} fraction > "
            f"{urban_threshold}) in {veg_fraction_path}; was the land cover "
            "generated with the urban tile enabled?"
        )

    source_files = source_files_by_variable(source_paths)
    missing = [b.variable for b in SOURCE_BANDS if b.variable not in source_files]
    if missing:
        raise ValueError(
            f"No source files provided for variables {missing}; "
            f"found files for: {sorted(source_files)}"
        )

    bands = {}
    for source_band in SOURCE_BANDS:
        source_cube = read_source_variable(
            source_files[source_band.variable], source_band, template
        )
        regridded = regrid_band(source_cube, template)
        bands[source_band.variable], n_filled = fill_invalid_urban_points(
            regridded, urban_mask
        )
        print(f"{source_band.variable}: filled {n_filled} urban points")

    output_cubes = iris.cube.CubeList(
        build_output_cube(field, bands, land_mask, urban_mask, template)
        for field in OUTPUT_FIELDS
    )

    save.netcdf(output_cubes, outfile)
    if not netcdf_only:
        save.ancil(output_cubes, outfile)


if __name__ == "__main__":
    args = _parse_args()
    main(
        args.sources,
        args.veg_fraction,
        args.urban_tile_id,
        args.urban_threshold,
        args.output,
        args.netcdf_only,
    )
