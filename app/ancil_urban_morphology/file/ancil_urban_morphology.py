#!/usr/bin/env python
"""
Urban morphology application
****************************

Derive the UCLEM urban morphology ancillary fields (STASH items 920-931) from
a directory of urban source (e.g. U-Surf v1.1) NetCDF files, one file per
variable, in five steps:

1. Generate the urban mask from the vegetation fraction ancillary. The target
   grid, land mask and urban mask are all taken from this file, so the
   application is independent of the model resolution.
2. Load the source file of each required variable into a single cubelist
   (e.g. global_HT_ROOF_1km_masked_gapfilled_QC_v1.1.nc). The file names are
   listed explicitly in this script. Values outside the valid range of each
   variable are masked.
3. Regrid the cubelist to the urban mask grid, as in the general regrid
   application. Urban points without a valid regridded value are filled from
   the nearest valid urban point, and non-urban points are masked.
4. Compute the remaining fields (canyon fraction and canyon vegetation
   fraction), add them to the cubelist and remove the fields that are no
   longer needed.
5. Fill the metadata of each field to be UM compliant (STASH indices), set
   non-urban land points to 0 and mask the ocean.

Options:
 * --veg-fraction : The vegetation fraction ancillary (NetCDF) defining the
   target grid, land points and the urban tile (pseudo level 15) fraction.
 * --urban-tile-id : The pseudo level of the urban tile (default 15).
 * --urban-threshold : Urban tile fraction above which a point is urban.
 * --output : the output file
Arguments:
 * The directory containing the urban source NetCDF files follows the options.
   Other files in the directory are ignored.

Example Usage:
ancil_urban_morphology.py --veg-fraction ${veg_frac} --output ${outfile} \
                          ${urban_source_dir}
"""

import os

import ants
import ants.decomposition
import iris
import iris.cube
import iris.fileformats.pp
import numpy

iris.FUTURE.save_split_attrs = True


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
        default=6,
        help="Pseudo level of the urban tile in the vegetation fractions",
    )
    parser.add_argument(
        "--urban-threshold",
        type=float,
        default=0.01,
        help="Urban tile fraction above which a point is considered urban",
    )
    args = parser.parse_args()
    if len(args.sources) != 1 or not os.path.isdir(args.sources[0]):
        parser.error("The source must be a single directory of urban NetCDF files")
    return args


def generate_urban_mask(veg_fraction_path, urban_tile_id, urban_threshold):
    """
    Step 1: generate the urban mask from the vegetation fractions.

    Returns the urban mask as a boolean cube on the target grid (True at urban
    points), usable as a regrid target, and the boolean land mask of the
    target grid. Urban points are land points where the urban tile fraction
    is above the threshold.
    """
    veg_fraction = ants.io.load.load_cube(veg_fraction_path, "vegetation_area_fraction")
    urban_fraction = veg_fraction.extract(iris.Constraint(pseudo_level=urban_tile_id))
    if urban_fraction is None:
        raise ValueError(
            f"No pseudo level {urban_tile_id} (urban tile) in {veg_fraction_path}"
        )

    land_mask = ~numpy.ma.getmaskarray(urban_fraction.data)
    urban_mask = land_mask & (urban_fraction.data.filled(0.0) > urban_threshold)
    if not urban_mask.any():
        raise ValueError(
            f"No urban points (pseudo level {urban_tile_id} fraction > "
            f"{urban_threshold}) in {veg_fraction_path}; was the land cover "
            "generated with the urban tile enabled?"
        )
    print(f"Land points: {land_mask.sum()}, urban points: {urban_mask.sum()}")

    urban_mask_cube = urban_fraction.copy(urban_mask)
    urban_mask_cube.remove_coord("pseudo_level")
    urban_mask_cube.rename("urban_mask")
    urban_mask_cube.units = "1"
    return urban_mask_cube, land_mask


def load_source_cubelist(source_directory):
    """
    Step 2: load the source file of each variable into a single cubelist. Each
    cube is named by the variable name of its source file.
    """
    # Set of source variables which share the file name pattern
    source_variables = [
        ("HT_ROOF", "roof_height"),
        ("CANYON_HWR", "canyon_height_to_width"),
        ("ALB_ROOF", "roof_albedo"),
        ("ALB_WALL", "wall_albedo"),
        ("ALB_IMPROAD", "impervious_road_albedo"),
        ("ALB_PERROAD", "pervious_road_albedo"),
        ("EM_ROOF", "roof_emissivity"),
        ("EM_WALL", "wall_emissivity"),
        ("EM_IMPROAD", "impervious_road_emissivity"),
        ("EM_PERROAD", "pervious_road_emissivity")
    ]

    file_name = lambda var: os.path.join(source_directory, f"global_{var}_1km_masked_gapfilled_QC_lon360_v1.1.nc")

    source_cubes = iris.cube.CubeList()
    for source_name, var_name in source_variables:
        path = file_name(source_name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Urban source file not found: {path}")
        cube = ants.io.load.load_cube(path, source_name)
        cube.rename(var_name)
        # The source sets "lon" for the longitude axis- it needs to be
        # "longitude" to be recognised by ants (for some reason "latitude" is
        # already set to its long form?)
        cube.coord("lon").rename("longitude")
        # Need to apply coordinate systems to the cube coords
        cube.coord("longitude").units = "degrees_east"
        cube.coord("latitude").units = "degrees_north"
        cube.coord("longitude").coord_system = ants.coord_systems.UM_SPHERE.crs
        cube.coord("latitude").coord_system = ants.coord_systems.UM_SPHERE.crs
        source_cubes.append(cube)

    # Two additional variables have a different file name pattern (minus _gapfilled)
    extra_variables = [
        ("WTLUNIT_ROOF", "roof_fraction"),
        ("WTROAD_PERV", "canyon_road_pervious_fraction")
    ]

    file_name = lambda var: os.path.join(source_directory, f"global_{var}_1km_masked_QC_lon360_v1.1.nc")

    for source_name, var_name in extra_variables:
        path = file_name(source_name)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Urban source file not found: {path}")
        cube = ants.io.load.load_cube(path, source_name)
        cube.rename(var_name)
        # The source sets "lon" for the longitude axis- it needs to be
        # "longitude" to be recognised by ants (for some reason "latitude" is
        # already set to its long form?)
        cube.coord("lon").rename("longitude")
        cube.coord("longitude").units = "degrees_east"
        cube.coord("latitude").units = "degrees_north"
        cube.coord("longitude").coord_system = ants.coord_systems.UM_SPHERE.crs
        cube.coord("latitude").coord_system = ants.coord_systems.UM_SPHERE.crs
        source_cubes.append(cube)

    return source_cubes


def regrid_cubes(source_cubes, target_cube):
    """Regrid each cube to the target with the configured regrid scheme."""
    scheme = ants.regrid.GeneralRegridScheme()
    return [source.regrid(target_cube, scheme) for source in source_cubes]


def regrid_cubelist(source_cubes, urban_mask_cube):
    """
    Step 3: regrid the cubelist to the grid of the urban mask, as in the
    general regrid application with the urban mask as the target. Urban points
    without a valid regridded value are filled from the nearest valid value,
    and non-urban points are masked.
    """
    regridded_cubes = ants.decomposition.decompose(
        regrid_cubes, source_cubes, urban_mask_cube
    )
    ants.analysis.make_consistent_with_lsm(
        regridded_cubes, urban_mask_cube, True, "spiral"
    )
    return iris.cube.CubeList(regridded_cubes)


def add_derived_fields(regridded_cubes):
    """
    Step 4: compute the canyon fraction and canyon vegetation fraction, and
    return a new cubelist with these added and the fields only needed to
    compute them removed.
    """
    # Fields which are only needed to compute the canyon fields
    intermediate_fields = ("roof_fraction", "canyon_road_pervious_fraction")

    roof_fraction = regridded_cubes.extract_cube("roof_fraction")
    canyon_road_pervious_fraction = regridded_cubes.extract_cube(
        "canyon_road_pervious_fraction"
    )

    canyon_fraction = roof_fraction.copy(1.0 - roof_fraction.data)
    canyon_fraction.rename("canyon_fraction")
    canyon_vegetation_fraction = canyon_fraction.copy(
        canyon_road_pervious_fraction.data * canyon_fraction.data
    )
    canyon_vegetation_fraction.rename("canyon_vegetation_fraction")

    retained_cubes = [
        cube for cube in regridded_cubes if cube.name() not in intermediate_fields
    ]
    return iris.cube.CubeList(
        retained_cubes + [canyon_fraction, canyon_vegetation_fraction]
    )


def fill_um_metadata(cubes, land_mask, urban_mask):
    """
    Step 5: make each field UM compliant by naming it, giving it a STASH
    index and units. Non-urban land points are set to 0 and ocean points are
    masked. Returns a new cubelist ordered by STASH item.
    """
    # Field name: (STASH item, UM name)
    um_fields = {
        "roof_height": (920, "UCLEM_BUILDING_HEIGHT"),
        "canyon_height_to_width": (921, "UCLEM_CANYON_HWR"),
        "canyon_fraction": (922, "UCLEM_WIDTH_RATIO"),
        "roof_albedo": (923, "UCLEM_ROOF_ALBEDO"),
        "wall_albedo": (924, "UCLEM_WALL_ALBEDO"),
        "impervious_road_albedo": (925, "UCLEM_ROAD_ALBEDO"),
        "canyon_vegetation_fraction": (926, "UCLEM_CANYON_VEG_FRACTION"),
        "pervious_road_albedo": (927, "UCLEM_CANYON_VEG_ALBEDO"),
        "roof_emissivity": (928, "UCLEM_ROOF_EMISSIVITY"),
        "wall_emissivity": (929, "UCLEM_WALL_EMISSIVITY"),
        "impervious_road_emissivity": (930, "UCLEM_ROAD_EMISSIVITY"),
        "pervious_road_emissivity": (931, "UCLEM_CANYON_VEG_EMISSIVITY"),
    }

    um_cubes = []
    for cube in cubes:
        stash_item, stash_name = um_fields[cube.name()]
        values = numpy.where(urban_mask, numpy.ma.filled(cube.data, 0.0), 0.0)
        um_cube = cube.copy(numpy.ma.masked_where(~land_mask, values))
        um_cube.rename(stash_name)
        um_cube.units = "1"
        um_cube.attributes = {"STASH": iris.fileformats.pp.STASH(1, 0, stash_item)}
        um_cubes.append(um_cube)
    return iris.cube.CubeList(
        sorted(um_cubes, key=lambda cube: cube.attributes["STASH"].item)
    )


def main(source_directory, veg_fraction_path, urban_tile_id, urban_threshold, outfile, netcdf_only):
    "main top/level"
    urban_mask_cube, land_mask = generate_urban_mask(
        veg_fraction_path, urban_tile_id, urban_threshold
    )
    source_cubes = load_source_cubelist(source_directory)
    regridded_cubes = regrid_cubelist(source_cubes, urban_mask_cube)
    all_fields = add_derived_fields(regridded_cubes)
    output_cubes = fill_um_metadata(
        all_fields, land_mask, urban_mask_cube.data
    )

    ants.io.save.netcdf(output_cubes, outfile)
    if not netcdf_only:
        ants.io.save.ancil(output_cubes, outfile)


if __name__ == "__main__":
    args = _parse_args()
    main(
        args.sources[0],
        args.veg_fraction,
        args.urban_tile_id,
        args.urban_threshold,
        args.output,
        args.netcdf_only,
    )
