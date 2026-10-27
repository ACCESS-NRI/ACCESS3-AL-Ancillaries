#!/usr/bin/env python
"""Build the cached N512 land/urban mask grid from a UM vegetation ancillary.

Run this script under the ACCESS mule environment, for example:

source /etc/bashrc
module use /g/data/hr22/modulefiles
module use ~access/modules
module load pythonlib/mule/2022.05.1
python make_class15_grid_cache.py --veg /path/to/qrparm.veg.frac_cci_n512e_urban --output qrparm_n512_class15_grid.npz
"""

from __future__ import print_function

import argparse

import mule
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--veg", required=True, help="UM vegetation ancillary with class-15 urban fraction")
    parser.add_argument("--output", required=True, help="Output NPZ cache path")
    parser.add_argument(
        "--urban-threshold",
        type=float,
        default=1.0e-12,
        help="Class-15 threshold used to mark urban points",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    veg_file = mule.AncilFile.from_file(args.veg)
    first_field = veg_file.fields[0]
    lon = first_field.bzx + first_field.bdx * np.arange(1, first_field.lbnpt + 1)
    lon_std = np.where(lon > 180.0, lon - 360.0, lon)
    lat = first_field.bzy + first_field.bdy * np.arange(1, first_field.lbrow + 1)

    class15 = None
    class15_bmdi = None
    for field in veg_file.fields:
        if getattr(field, "lbuser4", None) == 216 and getattr(field, "lbuser5", None) == 15:
            class15 = np.array(field.get_data(), dtype=np.float64)
            class15_bmdi = field.bmdi
            break

    if class15 is None:
        raise RuntimeError("class 15 not found in {}".format(args.veg))

    land_mask = class15 != class15_bmdi
    urban_mask = land_mask & (class15 > args.urban_threshold)
    np.savez(args.output, land_mask=land_mask, urban_mask=urban_mask, lon_std=lon_std, lat=lat)
    print("WROTE_GRID_CACHE", args.output)
    print("LAND_COUNT", int(land_mask.sum()))
    print("URBAN_COUNT", int(urban_mask.sum()))


if __name__ == "__main__":
    main()
