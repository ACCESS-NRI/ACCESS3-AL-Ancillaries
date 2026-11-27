# ancil_min_tile_fraction

`ancil_min_tile_fraction` runs after `ancil_split_grass_types` and applies a minimum tile fraction to the vegetation fractions: every tile with a fraction below `MIN_TILE_FRACTION` is set to 0.0, and the remaining tiles in the grid cell are scaled up so the fractions sum to 1.0. Its output is the final `qrparm.veg.frac` that downstream tasks read. Runs in the `um-env-ants` conda environment (`iris` and `ants`).

Where every tile in a grid cell is below the threshold, the largest tile is kept (and becomes 1.0). Masked (non-land) points are unchanged.

## Env Arguments

#### Inputs
* `VEGETATION_SOURCE`: Surface area fractions written by `ancil_split_grass_types`.

#### Outputs
* `OUTPUT`: Path to write the output. Writes to PP format and NetCDF format with the `.nc` extension.

#### Parameters
* `MIN_TILE_FRACTION`: Threshold in [0, 1]. Set from the `MIN_TILE_FRACTION` template variable in `rose-suite.conf`.
