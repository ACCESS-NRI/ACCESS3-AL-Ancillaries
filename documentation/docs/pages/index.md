<!-- # MODIFY -->
# CCI Ancillary Suite

The *CCI Ancillary Suite* is a Cylc8 workflow, with the Rose plugin, that can be used to generate atmosphere and land ancillaries for generation 3 ACCESS models (being ACCESS-AM3, ACCESS-CM3, ACCESS-rAM3, ACCESS-rCM3, as well as CABLE and JULES). The starting point for the workflow is the [ESA CCI Land Cover](https://climate.esa.int/en/projects/land-cover/) dataset- a global 300m resolution land cover class dataset. The land cover classes are mapped to surface types in the desired land model, and combined with various UKMO and published datasets, to arrive at a set of compatible ancillaries and forcings for the following applications:

* Regional Atmosphere-Land v3 (not including boundary or initial conditions).
* Global Atmosphere-Land v9 with climatological aerosols.
* Offline CABLE biogeophysics.
* Offline JULES.

The default targets are configured for NCI's Gadi machine, but should be portable to other machines with a Cylc installation, assuming the required input data is available.

## Configuring the Workflow

The workflow is intended to be configured via the options in the `rose-suite.conf` file, or via `rose edit`. The options are:

* `COMPUTE_PROJECT`: *string*, Which project to charge compute to.
* `LAND_MODEL`: *string*, Which land model to build ancillaries for. Sets the CCI land cover, LAI and canopy height mappings, and default soil layers and depth. Options are `"CABLE"` or `"JULES"`.
* `GRID_SOURCE`: *string*, Which source to use for the grid. Options are:
    - `"land_cover"`: Determine the grid from a UM grid namelist, and allow the CCI land cover to determine the land mask and land fractions.
    - `"land_sea_mask"`: Determine the grid from a supplied mask, and use the land mask for the remainder of the simulation. Not recommended for atmosphere-land simulations, as there is no method defined to determine land fractions.
    - `"ocean_mesh"`: Use an ESMF mesh, with a prescribed resolution or grid namelist, to determine the land mask and land fractions.
    - `"land_fractions"`: Use a land fractions ancillary to determine the grid and land sea mask.
* `RESOLUTION`: *string*, Target resolution, used with the `"ocean_mesh"` grid source. Can be either a UM resolution spec `"n<X>e"` or a UM grid file.
* `VERTICAL_DISCRETIZATION`: *string*, UM namelist describing the vertical discretization for atmosphere ancillaries.
* `CALENDAR`: *string*, Calendar to use for time dependent ancillaries. Options are `"360day"` and `"gregorian"`.
* `BEGIN_YEAR`: *int*, Starting year for time dependent ancillaries.
* `END_YEAR`: *int*, Ending year for time dependent ancillaries.
* `ATMOSPHERE_ANCILLARIES`: *bool*, Whether to generate atmosphere ancillaries for coupled simulations.
* `AEROSOLS`: *string*, Which version of the aerosols to create. Regional models like ACCESS-rAM3 use `"PP"`, while global models like ACCESS-AM3 use `"NetCDF"`.
* `URBAN`: *bool*, Whether to include urban fractions in the land cover to surface type mapping.
* `CCI_YEAR`: *int*, Which year to use from the CCI land cover dataset to use.
* `SOIL_INITIAL_CONDITIONS`: *bool*, Whether to generate soil initial conditions for the land model.
* `SOIL_INIT_CONDS_METHOD`: *string*, Method to use for generating soil initial conditions. Options are `"functional"`.

For more information about the tasks that makes up the workflow, see the [apps](apps/index.md) section for a visualisation of the graph and brief descriptions of each task.

## Running the Workflow

The workflow is run with Cylc8. After setting the configurable options, run the workflow with

```
cylc vip --run-name=<some_descriptive_name>
```

The `--run-name` is not required, but highly recommended as it makes it significantly easier to keep track of things when you've generated many sets of ancillaries. The cylc working directory is `/scratch/${PROJECT}/${USER}/cylc-run/CCI-Ancillary-Suite/<some_descriptive_name>` (on Gadi- this is configured centrally, so may vary from machine to machine). The outputs are written to `share/data` in the working directory. The output ancillaries are split by category in a hopefully logical basis, with the `preproc` directory containing files that were created during the workflow, but not required for the model runs.
