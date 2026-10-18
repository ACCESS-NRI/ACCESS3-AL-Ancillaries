# ancil_min_tile_fraction

`ancil_min_tile_fraction` is an optional `LAND_COVER_PREPROCESSING` step (`min-tile-fraction`) that sets every tile fraction below a threshold to 0.0, then proportionally rescales the remaining tiles in each grid cell so the cell sums to 1.0. Tiles with tiny fractions have a negligible effect on the simulation but cost the same compute time as large tiles. Steps run in the order listed in `LAND_COVER_PREPROCESSING`, so this step is best placed last, where it sees the final set of tiles.

If every tile in a cell is below the threshold, the cell's largest tile is set to 1.0. Masked (non-land) cells are unchanged.

## Env Arguments

#### Inputs
* `VEGETATION_SOURCE`: Surface area fractions to apply the minimum tile fraction to.

#### Outputs
* `OUTPUT`: Path to write the output. Writes to PP format and NetCDF format with the `.nc` extension. By default this is the same path as `VEGETATION_SOURCE`, so the app overwrites it in place- this lets `ancil_min_tile_fraction` be freely combined with the other `LAND_COVER_PREPROCESSING` steps regardless of which are selected. A copy of the NetCDF output is also written to `preproc/qrparm.veg.frac_ancil_min_tile_fraction.nc` for traceability.

#### Parameters
* `MIN_TILE_FRACTION`: Tile fractions below this value are set to 0.0. Default `0.01`.
