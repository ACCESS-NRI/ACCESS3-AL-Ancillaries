# vegfrac_postproc

`vegfrac_postproc` marks the end of the optional land cover post-processing steps. There are a series of post-processing tasks which can be applied to the tile fractions. The tasks used in a specific run are customisable, and able to be executed in any order.

## Choosing the steps

The steps are selected with `LAND_COVER_PREPROCESSING` in `rose-suite.conf`, and run in the order they are listed there, after `ancil_lct`. Every step reads and overwrites the same land cover fractions ancillary, so any subset can be combined in any order. Downstream tasks depend on `vegfrac_postproc`, which finishes once the last selected step has completed.

The order can change the result. For example, `split-grass-types` changes the tiles that `c4-fraction` and `min-tile-fraction` operate on, and `min-tile-fraction` is best placed last so that it rescales the final set of tiles.

## Available steps

* `c4-fraction`: [regrid_C4_fraction](../regrid_C4_fraction.md) and [ancil_C4_fraction](../ancil_C4_fraction.md)
* `fix-antarctic-permanent-ice`: [ancil_fix_antarctic_permanent_ice](../ancil_fix_antarctic_permanent_ice.md)
* `split-grass-types`: [regrid_ncar_lulcc](../regrid_ncar_lulcc.md) and [ancil_split_grass_types](../ancil_split_grass_types.md)
* `min-tile-fraction`: [ancil_min_tile_fraction](../ancil_min_tile_fraction.md)
