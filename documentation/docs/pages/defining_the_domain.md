# Defining the domain

There are a number of different ways to define the domain on which the ancillaries should be created. The method chosen also effects the way the land points are specified. These options correspond to the `GRID_SOURCE` template variable in `rose-suite.conf`. The methods available are:

1. [UM grid namelist](#um-grid-namelist) (`GRID_SOURCE='land_cover'`): Use a UM grid namelist to define the domain. The land points are determined by the source land cover dataset.
2. [Land-sea mask](#land-sea-mask) (`GRID_SOURCE='land_sea_mask'`): Use a predefined land-sea mask file, either in NetCDF or UM format. The land points are determined by the land mask.
3. [Ocean mesh](#ocean-mesh) (`GRID_SOURCE='ocean_mesh'`): Use an existing ESMF ocean mesh (as used by ACCESS ocean models), alongside a specified resolution. The land points are determined by points where the ocean mesh says the land fraction is >0.01. Currently available only for global domains accompanied by a resolution, specified in the UM format `n<XXX>e`. Regional domains with a grid namelist is a planned improvement. 
4. [Land fractions](#land-fractions) (`GRID_SOURCE='land_fractions'`): Use a land fractions NetCDF file. Requires a regular Cartesian grid. The land points are determined by points where the land fraction is >0.0.

### UM grid namelist

Usable by: ACCESS-AM3, ACCESS-rAM3, CABLE-standalone, JULES-standalone

The domain is defined by a UM grid namelist. When using a UM grid namelist, the generation of the land-sea mask is left up to the `ancil_lct` task, which uses the supplied land cover dataset to determine which points are land, ocean and the corresponding land fractions. The UM namelist is defined as:

```
&grid
    delta_lambda_targ   =   # Desired grid box size in x (typically degrees longitude)
    delta_phi_targ      =   # Desired grid box size in y (typically degrees latitude)
    points_lambda_targ  =   # Number of points in x
    points_phi_targ     =   # Number of points in y
    lambda_origin_targ  =   # Starting point in x (typically degrees longitude)
    phi_origin_targ     =   # Starting point in y (typically degrees latitude)
    lambda_pole         =   # Longitude pole location
    phi_pole            =   # Latitude pole location
    global              =   # Is domain global?
    inwsw               =   # Which corner to start in- 0 for for NW corner, 1 for SW corner
    igrid_targ          = 6 # Grid type- 6 for all ACCESS applications, denoting ENDGame grid
    rotated             = F # Whether to use rotated interpolation- recommended is false
/
```

Note that for global grids, both `points_X_targ` and `delta_X_targ` cannot be specified together, as one constrains the other.

### Land-sea mask

Usable by: CABLE-standalone, JULES-standalone

The domain is defined by a supplied land-sea mask file in NetCDF or UM format. Must be on a Cartesian grid. This is only usable by standalone land models, as there is no sensible way to determine fractional land. For NetCDF format files, requires the `"land_binary_mask"` variable with identifiable latitude and longitude coordinates. For UM format files, requires the `"land_binary_mask"` stash field.

### Ocean mesh

Usable by: ACCESS-AM3, CABLE-standalone, JULES-standalone

The domain is defined by a supplied ESMF ocean mesh. Recommended when it is desired to conform to an existing ocean/coupled model e.g. generating AM3 ancillaries that are compatible with a specific OM3 version for coupled model development. The land points are defined by the grid points which are calculated to have land fraction >0.01 by the ocean mesh that has been reinterpretaed onto a Cartesian grid.

### Land fractions

Usable by: ACCESS-AM3, ACCESS-rAM3, ACCESS-rCM3, CABLE-standalone, JULES-standalone

The domain is defined by a supplied land fractions file. Must be on a Cartesian grid. The land points are defined by grid points with land fraction >0.0.
