# Tiles with a very small area fraction have a negligible effect on the
# simulation, but cost the same compute time as a large tile. This sets every
# tile fraction below a threshold to 0.0, and proportionally rescales the
# remaining tiles in each grid cell so that the cell's fractions sum to 1.0.

import ants
import numpy

def _parse_args():
    parser = ants.AntsArgParser(
            target_lsm=False,
            target_grid=False
            )

    parser.add_argument(
            '--min-fraction',
            type=float,
            default=0.01,
            help='Tile fractions below this value are set to 0.0.'
            )

    return parser.parse_args()

def apply_minimum_tile_fraction(fractions, minimum_fraction):
    """
    Set tile fractions below minimum_fraction to 0.0 and rescale the remaining
    tiles so each land cell sums to 1.0.

    Parameters
    ----------
    fractions : numpy.ma.MaskedArray
        Tile fractions with the tile dimension on axis 0, and masked ocean
        cells.
    minimum_fraction : float
        Fractions strictly below this value are removed.

    Returns
    -------
    numpy.ma.MaskedArray
        The new fractions, with the same mask as the input. If every tile in a
        cell is below the threshold, the cell's largest tile is kept at 1.0.
    """

    mask = numpy.ma.getmaskarray(fractions)
    values = numpy.ma.filled(fractions, 0.0)
    land_cells = ~mask.all(axis=0)

    thresholded = numpy.where(values >= minimum_fraction, values, 0.0)
    cell_totals = thresholded.sum(axis=0)

    # Cells where every tile fell below the threshold keep their largest tile
    emptied_cells = land_cells & (cell_totals == 0.0)
    largest_tile = values.argmax(axis=0)[None, :, :]
    largest_tile_value = numpy.where(emptied_cells[None, :, :], 1.0, 0.0)
    numpy.put_along_axis(
            thresholded,
            largest_tile,
            numpy.where(
                emptied_cells[None, :, :],
                largest_tile_value,
                numpy.take_along_axis(thresholded, largest_tile, axis=0)
                ),
            axis=0
            )
    cell_totals = thresholded.sum(axis=0)

    safe_totals = numpy.where(cell_totals == 0.0, 1.0, cell_totals)
    rescaled = (thresholded / safe_totals[None, :, :]).astype(values.dtype)

    return numpy.ma.masked_array(rescaled, mask=mask)

def main(veg_fractions_file, minimum_fraction, output, netcdf_only):
    vegetation_fractions = ants.load_cube(
            veg_fractions_file,
            'vegetation_area_fraction'
            )

    vegetation_fractions.data = apply_minimum_tile_fraction(
            vegetation_fractions.data,
            minimum_fraction
            )

    ants.io.save.netcdf(vegetation_fractions, output)
    if not netcdf_only:
        ants.io.save.ancil(vegetation_fractions, output)

if __name__ == '__main__':
    args = _parse_args()
    main(args.sources, args.min_fraction, args.output, args.netcdf_only)
