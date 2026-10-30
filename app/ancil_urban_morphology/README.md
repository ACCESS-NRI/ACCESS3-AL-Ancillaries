# ancil_urban_morphology

The `ancil_urban_morphology` app derives the UCLEM urban morphology ancillary fields (STASH items 920-931) from a directory of U-Surf v1.1 GeoTIFFs, one file per variable. The target grid, land points and urban points are all taken from the vegetation fraction ancillary, so the app does not depend on the model resolution and no template ancillary is needed. The precise steps performed by the task are:

1. Load the vegetation fractions and extract the urban tile (pseudo level 15). Land points are those not masked, and urban points are land points where the urban tile fraction is above the urban threshold.
2. Read the first band (the value; any further bands are quality flags) of the GeoTIFF for each required variable, located by its exact U-Surf v1.1 file name (listed in the script, e.g. `global_HT_ROOF_1km_masked_gapfilled_QC_v1.1.tif`). Only the part of the source covering the target grid is read. Nodata values, and values outside the valid range of the variable (non-negative for `HT_ROOF` and `CANYON_HWR`, 0 to 1 for the others), are masked.
3. Regrid each variable to the target grid using the horizontal regridding scheme from the ANTS config.
4. Urban points with no valid regridded value are filled from the nearest valid urban point.
5. Derive the output fields. Non-urban land points are set to 0 and ocean points are masked.

| STASH item | Field | Derived from |
|---|---|---|
| 920 | `UCLEM_BUILDING_HEIGHT` | `HT_ROOF` |
| 921 | `UCLEM_CANYON_HWR` | `CANYON_HWR` |
| 922 | `UCLEM_WIDTH_RATIO` | `1 - WTLUNIT_ROOF` |
| 923 | `UCLEM_ROOF_ALBEDO` | `ALB_ROOF` |
| 924 | `UCLEM_WALL_ALBEDO` | `ALB_WALL` |
| 925 | `UCLEM_ROAD_ALBEDO` | `ALB_IMPROAD` |
| 926 | `UCLEM_CANYON_VEG_FRACTION` | `WTROAD_PERV * (1 - WTLUNIT_ROOF)` |
| 927 | `UCLEM_CANYON_VEG_ALBEDO` | `ALB_PERROAD` |
| 928 | `UCLEM_ROOF_EMISSIVITY` | `EM_ROOF` |
| 929 | `UCLEM_WALL_EMISSIVITY` | `EM_WALL` |
| 930 | `UCLEM_ROAD_EMISSIVITY` | `EM_IMPROAD` |
| 931 | `UCLEM_CANYON_VEG_EMISSIVITY` | `EM_PERROAD` |

The source must include files for the variables `HT_ROOF`, `CANYON_HWR`, `WTLUNIT_ROOF`, `WTROAD_PERV`, `ALB_ROOF`, `ALB_WALL`, `ALB_IMPROAD`, `ALB_PERROAD`, `EM_ROOF`, `EM_WALL`, `EM_IMPROAD` and `EM_PERROAD`. Other files in the source directory (e.g. `PCT_URBAN`) are ignored. The task fails if any of the expected files is missing, or if the vegetation fractions have no urban points (e.g. land cover generated with `URBAN=False`). The file names and valid ranges are the `*_FILE` constants in the script. Memory use scales with the size of the target domain, as the source is read at 1 km.

## Env Arguments

#### Inputs
* `URBAN_SOURCE_DIR`: Directory containing the U-Surf v1.1 GeoTIFFs, one per variable, with their original file names.
* `VEG_FRACTION_SOURCE`: Vegetation fractions (NetCDF, `qrparm.veg.frac.nc`) defining the target grid, land points and urban tile.

#### Outputs
* `OUTPUT`: Path to write the output to, in NetCDF format and, unless run with `netcdf_only`, also in UM ancillary format.

#### Parameters
* `ANTS_CONFIG`: ANTS config file. Typically the task's `rose-app.conf`.
* `--urban-tile-id` (command line, default 15): Pseudo level of the urban tile in the vegetation fractions.
* `--urban-threshold` (command line, default 1e-12): Urban tile fraction above which a point is urban.
