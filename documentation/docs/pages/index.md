<!-- # MODIFY -->
# ACCESS3-AL-Ancillary Workflow

The *ACCESS3-AL-Ancillary Workflow* is a Cylc8 workflow, with the Rose plugin, that can be used to generate atmosphere and land ancillaries for generation 3 ACCESS models (being ACCESS-AM3, ACCESS-CM3, ACCESS-rAM3, ACCESS-rCM3, as well as CABLE and JULES). The starting point for the workflow is the [ESA CCI Land Cover](https://climate.esa.int/en/projects/land-cover/) dataset- a global 300m resolution land cover class dataset. The land cover classes are mapped to surface types in the desired land model, and combined with various UKMO and published datasets, to arrive at a set of compatible ancillaries and forcings for the following applications:

* Regional Atmosphere-Land v3 (not including boundary or initial conditions).
* Global Atmosphere-Land v9 with climatological aerosols.
* Offline CABLE biogeophysics.
* Offline JULES.

The default targets are configured for NCI's Gadi machine, but should be portable to other machines with a Cylc installation, assuming the required input data is available. To get started with Rose/Cylc, see (for example) the [AM3 Rose/Cylc documentation](https://docs.access-hive.org.au/models/run_a_model/run_access-am3/#rosecylc-workflow-manager). The projects required to run this workflow on Gadi are:

* `hr11`
* `av17`
* `cm45`
* `access`

## Configuring the workflow

The workflow is intended to be configured the options in the `rose-suite.conf` file, which are exposed with the `rose edit` GUI.

### Model configurations

The workflow can be configured for multiple models, and it's not immediately obvious which settings are required for a given model. To this end, the target model is chosen with the `MODEL` option, and each model has its own set of default settings in the `rose-suite.conf`. These are prefixed by the model name, and are found under the `models` namespace in `rose edit`. Only the settings for the chosen `MODEL` are used, but the settings for all models must remain in the `rose-suite.conf`. The model specific settings and their defaults are:

| Setting | `ACCESS-AM3` (`AM3_`) | `ACCESS-rAM3` (`RAM3_`) | `ACCESS-rCM3` (`RCM3_`) | `CABLE-standalone` (`CABLE_STANDALONE_`) | `JULES-standalone` (`JULES_STANDALONE_`) |
|---|---|---|---|---|---|
| `LAND_MODEL` | `"CABLE"` | `"JULES"` | `"JULES"` | `"CABLE"` | `"JULES"` |
| `GRID_SOURCE` | `"ocean_mesh"` | `"land_cover"` | `"land_fractions"` | `"land_cover"` | `"land_cover"` |
| `ATMOSPHERE_ANCILLARIES` | `True` | `True` | `True` | `False` | `False` |
| `AEROSOLS` | `"NetCDF"` | `"PP"` | `"PP"` | `"NetCDF"` | `"NetCDF"` |
| `CALENDAR` | `"gregorian"` | `"360day"` | `"gregorian"` | `"360day"` | `"360day"` |

For example, the calendar used for ACCESS-rAM3 is set by `RAM3_CALENDAR`. The settings for the chosen model are also made available to every task as environment variables, without the prefix, e.g. `CALENDAR`.

The remaining options are shared by all models. The options that require user input are `COMPUTE_PROJECT`, the file to use as the domain definition (determined by the `GRID_SOURCE`) and the desired time period for workflows that require atmosphere ancillaries.

### Full option list

* `MODEL`: *string*, Which model to build ancillaries for. Selects which set of model specific settings (below) is used. Options are `"ACCESS-AM3"`, `"ACCESS-rAM3"`, `"ACCESS-rCM3"`, `"CABLE-standalone"` or `"JULES-standalone"`.

The model specific settings, each prefixed by the model prefix (e.g. `AM3_LAND_MODEL`):

* `<PREFIX>_LAND_MODEL`: *string*, Which land model to build ancillaries for. Sets the CCI land cover, LAI and canopy height mappings, and default soil layers and depth. Options are `"CABLE"` or `"JULES"`.
* `<PREFIX>_GRID_SOURCE`: *string*, Which source to use for the grid. Options are:
    - `"land_cover"`: Determine the grid from a UM grid namelist, and allow the CCI land cover to determine the land mask and land fractions.
    - `"land_sea_mask"`: Determine the grid from a supplied mask, and use the land mask for the remainder of the simulation. Not recommended for atmosphere-land simulations, as there is no method defined to determine land fractions.
    - `"ocean_mesh"`: Use an ESMF mesh, with a prescribed resolution or grid namelist, to determine the land mask and land fractions.
    - `"land_fractions"`: Use a land fractions ancillary to determine the grid and land sea mask.
* `<PREFIX>_ATMOSPHERE_ANCILLARIES`: *bool*, Whether to generate atmosphere ancillaries for coupled simulations.
* `<PREFIX>_AEROSOLS`: *string*, Which version of the aerosols to create. Regional models like ACCESS-rAM3 use `"PP"`, while global models like ACCESS-AM3 use `"NetCDF"`.
* `<PREFIX>_CALENDAR`: *string*, Calendar to use for time dependent ancillaries. Options are `"360day"` and `"gregorian"`.

The options shared by all models:

* `COMPUTE_PROJECT`: *string*, Which project to charge compute to.
* `GRID_NAMELIST`: *string*, Path to a UM grid namelist defining the grid. Used with the `"land_cover"` and `"ocean_mesh"` grid sources.
* `RESOLUTION`: *string*, Target atmosphere resolution as a UM resolution spec (e.g. `"n96e"`), used with the `"ocean_mesh"` grid source.
* `OCEAN_MESH`: *string*, Path to the ESMF ocean mesh. Only applicable when `GRID_SOURCE` is `"ocean_mesh"`.
* `LAND_FRACTIONS`: *string*, Path to a land fractions ancillary. Used with the `"land_fractions"` and `"land_sea_mask"` grid sources. With `"land_fractions"` it generates the mask and all downstream ancillaries; with `"land_sea_mask"` it is copied into the workspace and used to generate the ocean mask (for the ocean ancillaries) and the river ancillaries.
* `LAND_SEA_MASK`: *string*, Path to the land sea mask to use with the `"land_sea_mask"` grid source.
* `VERTICAL_DISCRETIZATION`: *string*, UM namelist describing the vertical discretization for atmosphere ancillaries.
* `BEGIN_YEAR`: *int*, Starting year for time dependent ancillaries.
* `END_YEAR`: *int*, Ending year for time dependent ancillaries.
* `URBAN`: *bool*, Whether to include urban fractions in the land cover to surface type mapping.
* `CCI_YEAR`: *int*, Which year to use from the CCI land cover dataset to use.
* `SOIL_INIT_CONDS_METHOD`: *string*, Method to use for generating soil initial conditions. Options are `"functional"`. Soil initial conditions, and a CABLE gridinfo file for offline CABLE, are only generated when `LAND_MODEL` is `"CABLE"`.
* `DEV_MODE`: *bool*, Used to keep the workflow alive during development.

For more information about the tasks that makes up the workflow, see the [apps](apps/index.md) section for a visualisation of the graph and brief descriptions of each task.

## Running the Workflow

The workflow is run with Cylc8. After setting the configurable options, run the workflow with

```
cylc vip --run-name=<name>
```

The `--run-name` is not required, but highly recommended as it makes it significantly easier to keep track of things when you've generated many sets of ancillaries. The cylc working directory is `/scratch/${PROJECT}/${USER}/cylc-run/CCI-Ancillary-Suite/<name>` (on Gadi- this is configured centrally, so may vary from machine to machine). 

## Accessing outputs

The outputs from the workflow are located under `/scratch/${PROJECT}/${USER}/cylc-run/ACCESS3-AL-Ancillaries/<name>`, where `${PROJECT}` is your default project, `${USER}` is your username and `<name>` is the name you gave the workflow when calling `cylc vip --run-name=<name>`. If no name was supplied, the `<name>` will be `runN`. This directory will also be symlinked in your home directory under `~/cylc-run/ACCESS3-AL-Ancillaries/<name>`.

This directory includes everything from the workflow run- the logs, the workspaces for each task and the ancillaries generated by the workflow. The ancillaries generated by the workflow are found under `share/data/` in this directory. The precise ancillaries that exist will depend on the workflow configuration, but they are separated into logical category folders e.g. `vegetation`, `ocean`.

### Other useful commands

* `cylc graph ACCESS3-AL-Ancillaries/<name>`: View the graph generated for your specific configuration.
* `cylc tui ACCESS3-AL-Ancillaries/<name>`: View the state of the workflow, trigger or stop tasks, view logs etc.
* `cylc vr ACCESS3-AL-Ancillaries/<name>`: Reinstall the workflow, pulling in any changes made since last install.
* `cylc stop ACCESS3-AL-Ancillaries/<name>`: Stop the workflow.
* `cylc clean ACCESS3-AL-Ancillaries/<name>`: Remove the workflow after it's finished or stopped.

See the [Cylc7 to Cylc8 cheat sheet](https://cylc.github.io/cylc-doc/stable/html/7-to-8/cheat-sheet.html) for a quick run down of the commands.

### Dev mode

You may be developing a script within the workflow, or testing different inputs to a given task in the workflow. Ideally, one would be able to retrigger specific tasks in the workflow to test these changes. This is difficult to do when a workflow finishes successfully, so `DEV_MODE` adds a task that's guaranteed to fail, so that the workflow always stays alive. With this active, you can make changes to a task, reload the workflow, then trigger just the desired task, or a desired task and any dependents of that task. Note that the workflow still shuts down after the last failure, but it can be awaked with `cylc play`. The typical workflow for modifying and triggering a specific task would be:

1. Modify the workflow with the desired changes.
2. Reinstall with the workflow with `cylc vr <workflow>/<name>`.
3. Wake the workflow with `cylc play <workflow>/<name>`.
4. Trigger the task with `cylc trigger <workflow>/<name>//<task_name>`.
