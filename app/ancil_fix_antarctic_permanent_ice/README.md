# ancil_fix_antarctic_permanent_ice

`ancil_fix_antarctic_permanent_ice` is a short task used to correct issues with classification of the antarctic region, which seem to be related to the removal of non-glacial ice in the `ancil_lct` task. At higher resolutions and land masks that include permanent ice as land, some points are spuriously identified as non-glacial ice and changed to bare soil, particularly when the land cover source's definition of land clashes with the land mask (typically ice shelves).

This task simply sets all land points below -60 degrees latitude to be 100% ice.

## Env Arguments

#### Inputs
* `VEGETATION_SOURCE`: Surface area fractions to apply the ice fix to.

#### Outputs
* `OUTPUT`: Path to write the output. Writes to PP format and NetCDF format with the `.nc` extension. By default this is the same path as `VEGETATION_SOURCE`, so the app overwrites it in place- this lets `ancil_fix_antarctic_permanent_ice` be freely combined with the CCI-Ancillary-Suite's other `LAND_COVER_PREPROCESSING` steps regardless of which are selected. A copy of the NetCDF output is also written to `preproc/qrparm.veg.frac_ancil_fix_antarctic_permanent_ice.nc` for traceability.

#### Parameters
* `MODEL_ICE_TILE`: Surface ID for the model's ice type.
