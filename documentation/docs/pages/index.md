<!-- # MODIFY -->
# CCI Ancillary Suite

The *CCI Ancillary Suite* is a Cylc8 workflow, with the Rose plugin, that can be used to generate atmosphere and land ancillaries for generation 3 ACCESS models (being ACCESS-AM3, ACCESS-CM3, ACCESS-rAM3, ACCESS-rCM3, as well as CABLE and JULES). The starting point for the workflow is the [ESA CCI Land Cover](https://climate.esa.int/en/projects/land-cover/) dataset- a global 300m resolution land cover class dataset. The land cover classes are mapped to surface types in the desired land model, and combined with various UKMO and published datasets, to arrive at a set of compatible ancillaries and forcings for the following applications:

* Regional Atmosphere-Land v3 (not including boundary or initial conditions).
* Global Atmosphere-Land v9 with climatological aerosols.
* Offline CABLE biogeophysics.
* Offline JULES.

The default targets are configured for NCI's Gadi machine, but should be portable to other machines with a Cylc installation, assuming the required input data is available.

## Configuring the Workflow

The workflow is intended to be configured via the options in the `rose-suite.conf` file, or via `rose edit`. The main choice is the target `MODEL`, which fixes the model specific options and the domain.

### Top level options

* `MODEL`: *string*, Which model to generate ancillaries for. Options are `"ACCESS-AM3"`, `"ACCESS-rAM3"`, `"ACCESS-rCM3"`, `"Offline-CABLE"` and `"Offline-JULES"`.
* `COMPUTE_PROJECT`: *string*, Which project to charge compute to.
* `BEGIN_YEAR`: *int*, Starting year for time dependent ancillaries.
* `END_YEAR`: *int*, Ending year for time dependent ancillaries.
* `CALENDAR`: *string*, Calendar to use for time dependent ancillaries. Options are `"360day"` and `"gregorian"`.
* `CCI_YEAR`: *int*, Which year to use from the CCI land cover dataset to use.
* `URBAN`: *bool*, Whether to include urban fractions in the land cover to surface type mapping.

### Model options

The following options are set by the chosen `MODEL`, in `models/<MODEL>.cylc`, and can't be set in the `rose-suite.conf`. To change them, edit the model file:

| Model | Land model | Atmosphere ancillaries | Aerosols | SST and sea ice | Domain |
|---|---|---|---|---|---|
| `ACCESS-AM3` | CABLE | Yes | NetCDF | Yes | 25km ACCESS-OM3 ocean mesh, N96 |
| `ACCESS-rAM3` | JULES | Yes | PP | Yes | `land_cover`, `GRID_NAMELIST` must be supplied |
| `ACCESS-rCM3` | CABLE | Yes | PP | No | `land_fractions`, `LAND_FRACTIONS` must be supplied |
| `Offline-CABLE` | CABLE | No | - | No | `land_cover`, `GRID_NAMELIST` must be supplied |
| `Offline-JULES` | JULES | No | - | No | `land_cover`, `GRID_NAMELIST` must be supplied |

* The land model sets the CCI land cover, LAI and canopy height mappings, and default soil layers and depth.
* The atmosphere models use the 85 level vertical discretization.
* Soil initial conditions, and a CABLE gridinfo file for offline CABLE, are generated for the CABLE models, using the `"functional"` method.

### Domain options

The domain is set by the `DOMAIN` dictionary in `models/<MODEL>.cylc`. The regional and offline models have no sensible default domain, so the grid file is given the placeholder `"SET-ME"`, and the workflow will refuse to validate until it is replaced. The domain options are:

* `GRID_SOURCE`: *string*, Which source to use for the grid. Options are:
    - `"land_cover"`: Determine the grid from a UM grid namelist, given by `GRID_NAMELIST`, and allow the CCI land cover to determine the land mask and land fractions.
    - `"land_sea_mask"`: Determine the grid from a supplied mask, given by `LAND_SEA_MASK`, and use the land mask for the remainder of the simulation. Not recommended for atmosphere-land simulations, as there is no method defined to determine land fractions.
    - `"ocean_mesh"`: Use an ESMF mesh, given by `OCEAN_MESH`, with a prescribed `RESOLUTION`, to determine the land mask and land fractions.
    - `"land_fractions"`: Use a land fractions ancillary, given by `LAND_FRACTIONS`, to determine the grid and land sea mask.
* `GRID_NAMELIST`: *string*, UM grid namelist, used with the `"land_cover"` grid source.
* `OCEAN_MESH`: *string*, ESMF ocean mesh, used with the `"ocean_mesh"` grid source.
* `RESOLUTION`: *string*, Target resolution, used with the `"ocean_mesh"` grid source. Can be either a UM resolution spec `"n<X>e"` or a UM grid file.
* `LAND_FRACTIONS`: *string*, Land fractions ancillary, used with the `"land_fractions"` grid source.
* `LAND_SEA_MASK`: *string*, Land sea mask, used with the `"land_sea_mask"` grid source.

### Adding a model

To add a new model, copy one of the files in `models/` to `models/<NEW_MODEL>.cylc` and modify the options. Then add the name to `VALID_MODELS` at the top of `flow.cylc`, and to the `MODEL` values in `meta/rose-meta.conf`.

For more information about the tasks that makes up the workflow, see the [apps](apps/index.md) section for a visualisation of the graph and brief descriptions of each task.

## Running the Workflow

The workflow is run with Cylc8. After setting the configurable options, run the workflow with

```
cylc vip --run-name=<name>
```

The `--run-name` is not required, but highly recommended as it makes it significantly easier to keep track of things when you've generated many sets of ancillaries. The cylc working directory is `/scratch/${PROJECT}/${USER}/cylc-run/CCI-Ancillary-Suite/<some_descriptive_name>` (on Gadi- this is configured centrally, so may vary from machine to machine). The outputs are written to `share/data` in the working directory. The output ancillaries are split by category in a hopefully logical basis, with the `preproc` directory containing files that were created during the workflow, but not required for the model runs.

### Other useful commands

* `cylc graph ACCESS3-AL-Ancillaries/<name>`: View the graph generated for your specific configuration.
* `cylc tui ACCESS3-AL-Ancillaries/<name>`: View the state of the workflow, trigger or stop tasks, view logs etc.
* `cylc vr ACCESS3-AL-Ancillaries/<name>`: Reinstall the workflow, pulling in any changes made since last install.
* `cylc stop ACCESS3-AL-Ancillaries/<name>`: Stop the workflow.
* `cylc clean ACCESS3-AL-Ancillaries/<name>`: Remove the workflow after it's finished or stopped.

See the [Cylc7 to Cylc8 cheat sheet](https://cylc.github.io/cylc-doc/stable/html/7-to-8/cheat-sheet.html) for a quick run down of the commands.
