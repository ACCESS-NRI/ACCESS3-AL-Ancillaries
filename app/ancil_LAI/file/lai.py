# (C) Crown Copyright, Met Office. All rights reserved.
#
import warnings

import ants
import iris
import numpy as np


MIN_LAI = 1e-10


def check_matching_horizontal_grid(source_cube, target_cube,
                                   tolerance_fraction=0.1):
    """
    Check that the source is on the same horizontal grid as the target.

    The coordinates may differ by a small amount (e.g. float precision
    differences introduced when the source was regridded and saved), but must
    agree to within a fraction of the smallest grid cell width.

    Parameters
    ----------
    source_cube : :class:`~iris.cube.Cube`
        Cube expected to be on the target grid.
    target_cube : :class:`~iris.cube.Cube`
        Cube defining the target grid.
    tolerance_fraction : float, optional
        Allowed coordinate difference, as a fraction of the smallest cell
        width of the target grid.

    Raises
    ------
    ValueError
        If the horizontal grids do not match.

    """
    source_coords = ants.utils.cube.horizontal_grid(source_cube)
    target_coords = ants.utils.cube.horizontal_grid(target_cube)
    for source_coord, target_coord in zip(source_coords, target_coords):
        if source_coord.shape != target_coord.shape:
            raise ValueError(
                f'The LAI source {source_coord.name()} has shape '
                f'{source_coord.shape}, but the land cover grid has shape '
                f'{target_coord.shape}. The LAI source must already be on '
                'the land cover grid (e.g. the output of regrid_LAI).')

        cell_widths = np.abs(np.diff(target_coord.points))
        tolerance = tolerance_fraction * (
            cell_widths.min() if cell_widths.size else 1.0)
        points_match = np.allclose(source_coord.points, target_coord.points,
                                   rtol=0, atol=tolerance)
        bounds_match = (
            not (source_coord.has_bounds() and target_coord.has_bounds())
            or np.allclose(source_coord.bounds, target_coord.bounds,
                           rtol=0, atol=tolerance))
        if not (points_match and bounds_match):
            raise ValueError(
                f'The LAI source {source_coord.name()} values differ from '
                f'the land cover grid by more than {tolerance}. The LAI '
                'source must already be on the land cover grid (e.g. the '
                'output of regrid_LAI).')


def subset_to_target_grid(source_cube, target_cube):
    """
    Extract the region of the source which exactly matches the target grid.

    The decomposition framework provides each target piece with a padded
    source piece.  Since the source is already on the target grid (with
    identical coordinates, see :func:`with_target_horizontal_coords`), the
    matching region is selected by exact coordinate matching rather than
    regridding.

    Parameters
    ----------
    source_cube : :class:`~iris.cube.Cube`
        Cube on the target grid, covering at least the target region.
    target_cube : :class:`~iris.cube.Cube`
        Cube defining the target region.

    Returns
    -------
    : :class:`~iris.cube.Cube`
        The source cube restricted to the target region.

    Raises
    ------
    ValueError
        If the source does not contain every target grid point.

    """
    slices = [slice(None)] * source_cube.ndim
    for source_coord, target_coord in zip(
            ants.utils.cube.horizontal_grid(source_cube),
            ants.utils.cube.horizontal_grid(target_cube)):
        matching_indices = np.flatnonzero(
            np.isin(source_coord.points, target_coord.points))
        if matching_indices.size != target_coord.shape[0]:
            raise ValueError(
                f'The LAI source {source_coord.name()} does not contain '
                'every point of the land cover grid.')
        slices[source_cube.coord_dims(source_coord)[0]] = matching_indices
    return source_cube[tuple(slices)]


def with_target_horizontal_coords(source_cube, target_cube):
    """
    Return a copy of the source with the target's horizontal coordinates.

    Used to remove float precision differences between the coordinates of
    datasets which are nominally on the same grid.

    Parameters
    ----------
    source_cube : :class:`~iris.cube.Cube`
        Cube already on the target grid (see
        :func:`check_matching_horizontal_grid`).
    target_cube : :class:`~iris.cube.Cube`
        Cube defining the target grid.

    Returns
    -------
    : :class:`~iris.cube.Cube`
        Copy of the source cube, with the target's horizontal coordinates.

    """
    aligned_cube = source_cube.copy()
    for source_coord, target_coord in zip(
            ants.utils.cube.horizontal_grid(aligned_cube),
            ants.utils.cube.horizontal_grid(target_cube)):
        coord_dims = aligned_cube.coord_dims(source_coord)
        aligned_cube.remove_coord(source_coord)
        aligned_cube.add_dim_coord(target_coord.copy(), coord_dims)
    return aligned_cube


def fill_missing_data(lct, lai):
    """
    Populate the LAI missing data with appropriate values.

    In-place operation to fill data which is missing accross some months by
    setting to 1e-10 Set unmasked LAI < 1e-10 to 1e-10

    Parameters
    ----------
    lct : :class:`~iris.cube.Cube`
        Land cover type fraction, used to define the landsea mask.
        (PFT, Y, X).
    lai : :class:`~iris.cube.Cube`
        The LAI we want to process for missing data (TIME, Y, X).

    """
    dates = lai.coord('time').units.num2date(
        lai.coord('time').points)
    years = set([date.year for date in dates])
    months = sorted([date.month for date in dates])
    if len(years) != 1 or range(1, 13) != months:
        msg = ('Filling of LAI data expects a 12 month climatology for LAI '
               'total.\n{}')
        ValueError(msg.format(lai.coord('time')))

    # Apply the landsea mask
    pdim = lct.coord_dims(lct.coord('pseudo_level'))[0]
    lai.data[..., np.ma.getmaskarray(lct[pdim].data)] = np.ma.masked

    # Missing values across SOME months (i.e. values are missing across some
    # rather than all months).  Set these points to min_lai.
    tdim = lai.coord_dims(lai.coord('time'))[0]
    nn_missing = lai.data.mask.sum(axis=tdim)
    nn_missing = (nn_missing > 0) * (nn_missing < lai.shape[tdim])
    lai.data[lai.data.mask * nn_missing] = MIN_LAI

    # Those missing accross all months are handled when making the LAI
    # consistent with the coastlines (i.e. through nearest neighbour)

    # Set unmasked points with < minimum lai to the minimum LAI.
    lai.data[
        (lai.data.data <= MIN_LAI) * ~np.ma.getmaskarray(lai.data)] = MIN_LAI


def _calc_lai(lct, lai_total, relative_weights):
    """
    Calculate LAI by solving a set of linear equations through substitution.

    Where the total vegetation fraction (for the functional types) equals less
    than 10% of a grid box but non-zero, each LAI PFT is masked (to be filled
    using nearest neighbour when ensuring consistency with the lct coastlines).

    Parameters
    ----------
    lct : :class:`numpy.ndarray`
        The vegetation fraction array with order (pseudo-level, y, x).
    lai_total : numpy.ndarray
        The total lai array with order (t, y, x).
    relative_weights : :class:`numpy.ndarray`
        An array representing the relative weights between LAI classes.

    Returns
    -------
    : numpy.ndarray
        LAI result for each functional type (t, pseudo-level, y, x).

    """
    # Solve the set of linear equations using forward substitution.
    t1 = (relative_weights[:, None, None] * lct).sum(axis=0)
    t2 = relative_weights[:, None, None, None] * lai_total
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = t2 / t1
    if result.ndim != 4:
        msg = 'Unexpeced dimensionality: {}D, expecting {}D'
        raise ValueError(msg.format(result.ndim, 4))

    timedim = 1
    pldim = 0
    # Make our result (time, pseudo-level, y, x)
    result = result.transpose(timedim, pldim, 2, 3)
    # Set lai to zero where there is zero vegetation fraction.
    result[:, lct == 0] = 0
    # Set lai to zero where there is no total LAI.
    result.transpose(1, 0, 2, 3)[:, lai_total <= 0] = 0

    # Define a minimum veg fraction threshold (this ensures that the LAI
    # resolved doesn't give unreasonably high LAI PFTs in the case of a high
    # total LAI).  This threshold value was chosen by Martin Best.
    # We mask these elements which is then filled by nearest neighbour.
    min_veg_threshold = 0.2
    total_veg = lct.sum(axis=0)
    if not np.ma.is_masked(result):
        result = np.ma.array(result)
    result[..., (total_veg < min_veg_threshold) * (total_veg > 0)] = (
        np.ma.masked)

    # Ensure we retain the mask from the total LAI field (we may have been
    # overridden by the previous steps).
    if np.ma.is_masked(lai_total):
        result.mask.transpose(1, 0, 2, 3)[:, lai_total.mask] = True
    return result


def calc_lai(relative_weights, lai_total, lct):
    """
    Calculate the LAI for the vegetation fraction functional types.

    Parameters
    ----------
    relative_weights : dict
        Dictionary containing both weights ('relative_weights') and mappings
        ('jules_classes').
    lct : :class:`~iris.cube.Cube`
        Land cover type fraction ancillary containing the functional type
        classes.
    lai_total : :class:`~iris.cube.Cube`
        Total leaf area index data, already on the grid of the land cover
        type fraction (see :func:`check_matching_horizontal_grid`).

    Returns
    -------
    : :class:`~iris.cube.Cube`
        Lai corresponding to each functional type.

    """
    x, y = ants.utils.cube.horizontal_grid(lct)

    # Extract functional types.
    slices = ants.analysis.cover_mapping.fetch_lct_slices(
        lct, relative_weights['jules_classes'])
    functional_types = lct[slices]

    # The LAI is already on the lct grid, so extract the region matching this
    # (possibly decomposed) piece of the lct rather than regridding.  Mask any
    # invalid values so that they are filled by nearest neighbour.
    lai_subset = subset_to_target_grid(lai_total, lct)
    lai_tar = lai_subset.copy(np.ma.masked_invalid(lai_subset.data))
    fill_missing_data(functional_types, lai_tar)

    # Calculate the LAI for the functional types.
    results = _calc_lai(functional_types.data, lai_total.data,
                        relative_weights['relative_weights'])

    # Tidy-up the resulting cubes metadata.
    lai_res = iris.cube.Cube(results)
    lai_res.standard_name = 'leaf_area_index'
    lai_res.units = 1
    lai_res.attributes['STASH'] = iris.fileformats.pp.STASH.from_msi(
        'm01s00i217')
    lai_res.add_dim_coord(y, 2)
    lai_res.add_dim_coord(x, 3)
    lai_res.add_aux_coord(functional_types.coord('pseudo_level'), 1)
    lai_res.add_dim_coord(lai_tar.coord('time'), 0)

    # Set unmasked points with < minimum lai to the minimum LAI.
    lai_res.data[(lai_res.data.data <= MIN_LAI) * ~lai_res.data.mask] = MIN_LAI

    return lai_res
