#!/usr/bin/env python
"""Write/update a UM ancillary from a payload NPZ containing stash_XXX arrays.

Run this script under the ACCESS mule environment, for example:

source /etc/bashrc
module use /g/data/hr22/modulefiles
module use ~access/modules
module load pythonlib/mule/2022.05.1
python write_uclem_ancil_from_npz.py --base qrparm.MORUSES.morph_new --payload fields.npz --output qrparm.USURF.uclem_morph_920_931 --overwrite
"""

from __future__ import print_function

import argparse
import shutil
import time

import mule
import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base ancillary path")
    parser.add_argument("--payload", required=True, help="NPZ with stash_XXX arrays")
    parser.add_argument("--output", required=True, help="Output ancillary path")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the output path")
    parser.add_argument(
        "--backup-existing",
        action="store_true",
        help="Create a timestamped backup before overwriting an existing output file",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.overwrite and args.output != args.base:
        try:
            open(args.output, "rb").close()
        except IOError:
            pass
        else:
            raise IOError("{} already exists; pass --overwrite to replace it".format(args.output))

    backup_path = None
    if args.backup_existing:
        try:
            open(args.output, "rb").close()
        except IOError:
            pass
        else:
            timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
            backup_path = args.output + ".bak_" + timestamp
            shutil.copy2(args.output, backup_path)

    payload = np.load(args.payload)
    umfile = mule.load_umfile(args.base)
    fields_by_stash = {}
    for field in umfile.fields:
        fields_by_stash[getattr(field, "lbuser4", None)] = field
    template = umfile.fields[0]

    for payload_name in sorted(payload.files):
        stash = int(payload_name.split("_")[1])
        values = payload[payload_name]
        field = fields_by_stash.get(stash)
        if field is None:
            field = template.copy()
            field.lbuser4 = stash
            field.lbuser5 = 0
            field.lbuser6 = 0
            field.set_data_provider(mule.ArrayDataProvider(values))
            umfile.fields.append(field)
            fields_by_stash[stash] = field
        else:
            field.set_data_provider(mule.ArrayDataProvider(values))

    umfile.fields = sorted(umfile.fields, key=lambda field: getattr(field, "lbuser4", -1))
    tmp_path = args.output + ".tmp_" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    umfile.to_file(tmp_path)
    shutil.move(tmp_path, args.output)

    print("WROTE", args.output)
    if backup_path is not None:
        print("BACKUP", backup_path)
    print("FIELD_CODES", [getattr(field, "lbuser4", None) for field in umfile.fields])


if __name__ == "__main__":
    main()
