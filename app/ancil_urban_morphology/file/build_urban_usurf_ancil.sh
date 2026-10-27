#!/usr/bin/env bash
set -euo pipefail

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi
}

for name in USURF_DIR VEG GRID_CACHE PAYLOAD SUMMARY_JSON OUTPUT; do
  require_var "$name"
done

if [[ -z "${BASE:-}" ]]; then
  require_var MORPHOLOGY_TEMPLATE_DIR
  require_var RESOLUTION
  resolution_key="${RESOLUTION%e}"
  BASE="${MORPHOLOGY_TEMPLATE_DIR%/}/${resolution_key}/qrparm.MORUSES.morph"
fi

for required_file in "$VEG" "$BASE"; do
  if [[ ! -f "$required_file" ]]; then
    echo "Missing required input file: $required_file" >&2
    exit 1
  fi
done

if [[ ! -d "$USURF_DIR" ]]; then
  echo "Missing U-Surf GeoTIFF directory: $USURF_DIR" >&2
  exit 1
fi

mkdir -p "$(dirname "$GRID_CACHE")" "$(dirname "$PAYLOAD")" "$(dirname "$SUMMARY_JSON")" "$(dirname "$OUTPUT")"

set +u
source /etc/bashrc
set -u

if [[ ! -f "$GRID_CACHE" ]]; then
  module use /g/data/hr22/modulefiles
  module use ~access/modules
  module load pythonlib/mule/2022.05.1
  python -u make_class15_grid_cache.py \
    --veg "$VEG" \
    --output "$GRID_CACHE"
fi

module use /g/data/xp65/public/modules
module load conda/analysis3-25.10
python -u generate_qrparm_usurf_uclem_ancil.py \
  --usurf-dir "$USURF_DIR" \
  --veg "$VEG" \
  --base "$BASE" \
  --grid-cache "$GRID_CACHE" \
  --final-npz "$PAYLOAD" \
  --summary-json "$SUMMARY_JSON" \
  --output "$OUTPUT"

module use /g/data/hr22/modulefiles
module use ~access/modules
module load pythonlib/mule/2022.05.1
python -u write_uclem_ancil_from_npz.py \
  --base "$BASE" \
  --payload "$PAYLOAD" \
  --output "$OUTPUT" \
  --overwrite
