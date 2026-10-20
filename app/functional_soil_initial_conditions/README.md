# functional_soil_initial_conditions

The `functional_soil_initial_conditions` app generates basic soil moisture and soil temperature initial conditions for the land model, from simple functional forms. It is run when `SOIL_INITIAL_CONDITIONS` is enabled and `SOIL_INIT_CONDS_METHOD` is `"functional"`. The resulting initial conditions should be valid enough to begin a spin-up of a land model, but should not be used for short time scale simulations where the initial condition is important. The precise steps performed by the task are:

1. Load the volumetric soil moisture content at saturation (`sm_sat`) from the soil parameters ancillary. This also determines the grid and the land points of the output.
2. Generate the soil moisture by setting every soil layer to saturation. With `volumetric` moisture units, the output is the volumetric soil moisture content at saturation (m3 m-3). With `mass` moisture units, it is scaled by the density of water and the thickness of each layer to give the mass of water in each layer (kg m-2).
3. Generate the soil temperature, which varies linearly with latitude from `MAX_TEMPERATURE` (degC) at the equator to 0 degC at the poles, and is the same in every soil layer. The output is converted to K.
4. Save the soil moisture (`volumetric_soil_moisture_content_in_a_layer` or `mass_content_of_water_in_soil_layer`) and soil temperature (`soil_temperature`) to NetCDF, with a `depth` coordinate at the centre of each soil layer.

## Env Arguments

#### Inputs
* `SOIL_PARAMETERS`: Soil parameters ancillary (NetCDF), from the `merge_soils` app. Must contain `sm_sat`.

#### Outputs
* `OUTPUT`: Path to write the soil initial conditions to, in NetCDF format.

#### Parameters
* `MODEL_SOIL_THICKNESS`: Comma separated list of the thickness of each soil layer (m), from the surface downwards. Set in `flow.cylc` based on `LAND_MODEL`, but can be overridden in this app's `rose-app.conf`.
* `MOISTURE_UNITS`: Units of the soil moisture, either `volumetric` (m3 m-3) or `mass` (kg m-2). Set in `flow.cylc` based on `LAND_MODEL` (`volumetric` for CABLE, `mass` for JULES), but can be overridden in this app's `rose-app.conf`.
* `MAX_TEMPERATURE`: Soil temperature (degC) at the equator.
