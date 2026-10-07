# Apps

The CCI Ancillary Suite is built from a set of Rose apps, one per task in the workflow. Each app has its own page in this section, describing what it does and the inputs, outputs and parameters it takes. The pages are the same as the `README.md` files in each app's directory in the repository.

The graph below shows how the apps depend on each other. Click an app to go to its page. Apps inside a dashed box are only included in the workflow when the stated option in `rose-suite.conf` takes that value; all other apps are always run.

```mermaid
flowchart LR
    preprocess_CCI_water --> ancil_lct

    subgraph grid_ocean_mesh ["GRID_SOURCE = ocean_mesh"]
        landseamask_from_ocean_mesh
    end
    subgraph grid_land_fractions ["GRID_SOURCE = land_fractions"]
        landseamask_from_land_fractions
    end
    landseamask_from_ocean_mesh --> ancil_lct
    landseamask_from_land_fractions --> ancil_lct

    ancil_lct --> regrid_ncar_lulcc
    ancil_lct --> ancil_fix_antarctic_permanent_ice
    regrid_ncar_lulcc --> ancil_split_grass_types
    ancil_fix_antarctic_permanent_ice --> ancil_split_grass_types
    ancil_lct --> regrid_LAI
    ancil_split_grass_types --> ancil_LAI
    regrid_LAI --> ancil_LAI
    ancil_LAI --> ancil_canopy_height
    ancil_LAI --> merge_veg_func
    ancil_canopy_height --> merge_veg_func
    ancil_split_grass_types --> ancil_soil_hydrology
    ancil_split_grass_types --> ancil_topographic_index
    ancil_split_grass_types --> ancil_soil_albedo
    ancil_soil_hydrology --> merge_soils
    ancil_soil_albedo --> merge_soils
    ancil_split_grass_types --> ancil_soil_dust
    merge_soils --> ancil_soil_dust
    ancil_lct --> ancil_soil_roughness
    ancil_LAI --> ancil_soil_roughness

    subgraph soil_init ["SOIL_INITIAL_CONDITIONS = true"]
        functional_soil_initial_conditions
    end
    ancil_soil_hydrology --> functional_soil_initial_conditions

    subgraph atmosphere ["ATMOSPHERE_ANCILLARIES = true"]
        ancil_orographic_formdrag_preproc --> ancil_orographic_formdrag
        ancil_orography_unfiltered_preproc --> ancil_orography_mean
        ancil_orography_mean --> ancil_orographic_wavedrag
        ancil_orography_filtered_preproc --> ancil_orographic_wavedrag
        ancil_orographic_wavedrag --> regrid_ozone
        ancil_orography_unfiltered_preproc --> ancil_radiation_parameters
        ancil_river_routing_preproc --> ancil_river_routing
        ancil_river_routing --> ancil_river_storage_preproc --> ancil_river_storage
        ancil_clim_dms
        ancil_clim_sea
        regrid_seaice_reynolds
        regrid_SST_reynolds

        subgraph aerosols_netcdf ["AEROSOLS = NetCDF"]
            ancil_aeroclim_preproc --> regrid_aerosol
        end
        subgraph aerosols_pp ["AEROSOLS = PP"]
            regrid_seasalt_aerosol
            regrid_biog_aerosol
            regrid_biom_aerosol
            regrid_ocff_aerosol
            regrid_sulp_aerosol
            regrid_blck_aerosol
            regrid_dust_aerosol
        end
    end
    ancil_lct --> ancil_orographic_formdrag
    ancil_lct --> ancil_orography_mean
    ancil_lct --> ancil_radiation_parameters
    ancil_lct --> ancil_clim_dms
    ancil_lct --> ancil_clim_sea
    ancil_lct --> regrid_seaice_reynolds
    ancil_lct --> regrid_SST_reynolds
    ancil_lct --> ancil_river_routing
    ancil_orographic_wavedrag --> regrid_aerosol
    ancil_orographic_wavedrag --> regrid_seasalt_aerosol
    ancil_orographic_wavedrag --> regrid_biog_aerosol
    ancil_orographic_wavedrag --> regrid_biom_aerosol
    ancil_orographic_wavedrag --> regrid_ocff_aerosol
    ancil_orographic_wavedrag --> regrid_sulp_aerosol
    ancil_orographic_wavedrag --> regrid_blck_aerosol
    ancil_orographic_wavedrag --> regrid_dust_aerosol

    click ancil_LAI "ancil_LAI/" "Documentation for ancil_LAI"
    click ancil_aeroclim_preproc "ancil_aeroclim_preproc/" "Documentation for ancil_aeroclim_preproc"
    click ancil_canopy_height "ancil_canopy_height/" "Documentation for ancil_canopy_height"
    click ancil_clim_dms "ancil_clim_dms/" "Documentation for ancil_clim_dms"
    click ancil_clim_sea "ancil_clim_sea/" "Documentation for ancil_clim_sea"
    click ancil_fix_antarctic_permanent_ice "ancil_fix_antarctic_permanent_ice/" "Documentation for ancil_fix_antarctic_permanent_ice"
    click ancil_lct "ancil_lct/" "Documentation for ancil_lct"
    click ancil_orographic_formdrag "ancil_orographic_formdrag/" "Documentation for ancil_orographic_formdrag"
    click ancil_orographic_formdrag_preproc "ancil_orographic_formdrag_preproc/" "Documentation for ancil_orographic_formdrag_preproc"
    click ancil_orographic_wavedrag "ancil_orographic_wavedrag/" "Documentation for ancil_orographic_wavedrag"
    click ancil_orography_filtered_preproc "ancil_orography_filtered_preproc/" "Documentation for ancil_orography_filtered_preproc"
    click ancil_orography_mean "ancil_orography_mean/" "Documentation for ancil_orography_mean"
    click ancil_orography_unfiltered_preproc "ancil_orography_unfiltered_preproc/" "Documentation for ancil_orography_unfiltered_preproc"
    click ancil_radiation_parameters "ancil_radiation_parameters/" "Documentation for ancil_radiation_parameters"
    click ancil_river_routing "ancil_river_routing/" "Documentation for ancil_river_routing"
    click ancil_river_routing_preproc "ancil_river_routing_preproc/" "Documentation for ancil_river_routing_preproc"
    click ancil_river_storage "ancil_river_storage/" "Documentation for ancil_river_storage"
    click ancil_river_storage_preproc "ancil_river_storage_preproc/" "Documentation for ancil_river_storage_preproc"
    click ancil_soil_albedo "ancil_soil_albedo/" "Documentation for ancil_soil_albedo"
    click ancil_soil_dust "ancil_soil_dust/" "Documentation for ancil_soil_dust"
    click ancil_soil_hydrology "ancil_soil_hydrology/" "Documentation for ancil_soil_hydrology"
    click ancil_soil_roughness "ancil_soil_roughness/" "Documentation for ancil_soil_roughness"
    click ancil_split_grass_types "ancil_split_grass_types/" "Documentation for ancil_split_grass_types"
    click ancil_topographic_index "ancil_topographic_index/" "Documentation for ancil_topographic_index"
    click landseamask_from_ocean_mesh "landseamask_from_ocean_mesh/" "Documentation for landseamask_from_ocean_mesh"
    click merge_soils "merge_soils/" "Documentation for merge_soils"
    click merge_veg_func "merge_veg_func/" "Documentation for merge_veg_func"
    click preprocess_CCI_water "preprocess_CCI_water/" "Documentation for preprocess_CCI_water"
    click regrid_LAI "regrid_LAI/" "Documentation for regrid_LAI"
    click regrid_SST_reynolds "regrid_SST_reynolds/" "Documentation for regrid_SST_reynolds"
    click regrid_aerosol "regrid_aerosol/" "Documentation for regrid_aerosol"
    click regrid_biog_aerosol "regrid_biog_aerosol/" "Documentation for regrid_biog_aerosol"
    click regrid_biom_aerosol "regrid_biom_aerosol/" "Documentation for regrid_biom_aerosol"
    click regrid_blck_aerosol "regrid_blck_aerosol/" "Documentation for regrid_blck_aerosol"
    click regrid_dust_aerosol "regrid_dust_aerosol/" "Documentation for regrid_dust_aerosol"
    click regrid_ncar_lulcc "regrid_ncar_lulcc/" "Documentation for regrid_ncar_lulcc"
    click regrid_ocff_aerosol "regrid_ocff_aerosol/" "Documentation for regrid_ocff_aerosol"
    click regrid_ozone "regrid_ozone/" "Documentation for regrid_ozone"
    click regrid_seaice_reynolds "regrid_seaice_reynolds/" "Documentation for regrid_seaice_reynolds"
    click regrid_seasalt_aerosol "regrid_seasalt_aerosol/" "Documentation for regrid_seasalt_aerosol"
    click regrid_sulp_aerosol "regrid_sulp_aerosol/" "Documentation for regrid_sulp_aerosol"

    classDef unlinked stroke-dasharray:2 2,color:#777
    class functional_soil_initial_conditions,landseamask_from_land_fractions unlinked
    style grid_ocean_mesh stroke-dasharray:6 4,fill:none
    style grid_land_fractions stroke-dasharray:6 4,fill:none
    style soil_init stroke-dasharray:6 4,fill:none
    style atmosphere stroke-dasharray:6 4,fill:none
    style aerosols_netcdf stroke-dasharray:6 4,fill:none
    style aerosols_pp stroke-dasharray:6 4,fill:none
```
