# Applies a minimum tile fraction to the vegetation fractions. Every tile with
# a fraction below the threshold is set to 0.0, and the surviving tiles are
# scaled up so that the fractions in each grid cell sum to 1.0 again.
#
# If every tile in a grid cell is below the threshold (e.g. a threshold of 0.3
# on a cell split evenly between 4 tiles), removing them all would leave
# nothing to scale up. In that case the largest tile in the cell is kept, and
# so ends up with a fraction of 1.0.

import ants
import numpy


def _parse_args():
    parser = ants.AntsArgParser(
            target_lsm=False,
            target_grid=False
            )

    parser.add_argument(
            '--min-tile-fraction',
            type=float,
            required=True,
            help='Tile fractions below this value are set to 0.0.'
            )

    return parser.parse_args()


def apply_minimum_tile_fraction(tile_fractions, min_tile_fraction):
    """
    Set all tile fractions below the threshold to 0.0 and rescale the remaining
    tiles so that they sum to 1.0. The tile axis is the first axis of the data.
    Masked (non-land) points are left untouched.
    """
    fractions = numpy.ma.getdata(tile_fractions)
    land_mask = ~numpy.ma.getmaskarray(tile_fractions)

    keep_tile = (fractions >= min_tile_fraction) & land_mask

    # Cells where every tile is below the threshold keep their largest tile
    land_cells_without_tiles = ~keep_tile.any(axis=0) & land_mask.all(axis=0)
    largest_tile = numpy.argmax(numpy.where(land_mask, fractions, -1.0), axis=0)
    keep_largest = (
        numpy.arange(fractions.shape[0])[:, None, None] == largest_tile[None]
    ) & land_cells_without_tiles[None]
    keep_tile = keep_tile | keep_largest

    thresholded = numpy.where(keep_tile, fractions, 0.0)
    tile_total = thresholded.sum(axis=0)

    # A cell whose kept tiles all have a fraction of 0.0 can't be rescaled
    safe_total = numpy.where(tile_total > 0.0, tile_total, 1.0)
    rescaled = thresholded / safe_total[None]

    return numpy.ma.masked_array(
            numpy.where(land_mask, rescaled, fractions),
            mask=~land_mask
            )


def main(veg_fractions_file, min_tile_fraction, output, netcdf_only):
    if not 0.0 <= min_tile_fraction <= 1.0:
        raise ValueError(
            f'The minimum tile fraction must be in [0, 1], got {min_tile_fraction}'
            )

    vegetation_fractions = ants.load_cube(
            veg_fractions_file,
            'vegetation_area_fraction'
            )

    vegetation_fractions.data = apply_minimum_tile_fraction(
            vegetation_fractions.data,
            min_tile_fraction
            )

    ants.io.save.netcdf(vegetation_fractions, output)
    if not netcdf_only:
        ants.io.save.ancil(vegetation_fractions, output)


if __name__ == '__main__':
    args = _parse_args()
    main(args.sources, args.min_tile_fraction, args.output, args.netcdf_only)
