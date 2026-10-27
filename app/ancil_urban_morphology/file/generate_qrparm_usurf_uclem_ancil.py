#!/usr/bin/env python3
"""Generate a U-Surf-driven UCLEM ancillary without changing source code.

This script creates a UM ancillary based on ``qrparm.MORUSES.morph_new`` and
updates/adds the following fields:

- 920  UCLEM building height                 <- HT_ROOF
- 921  UCLEM canyon H/W ratio                <- CANYON_HWR
- 922  UCLEM width ratio                     <- 1 - WTLUNIT_ROOF
- 923  UCLEM roof albedo                     <- ALB_ROOF
- 924  UCLEM wall albedo                     <- ALB_WALL
- 925  UCLEM road albedo                     <- ALB_IMPROAD
- 926  UCLEM canyon vegetation fraction      <- WTROAD_PERV * (1 - WTLUNIT_ROOF)
- 927  UCLEM canyon vegetation albedo        <- ALB_PERROAD
- 928  UCLEM roof emissivity                 <- EM_ROOF
- 929  UCLEM wall emissivity                 <- EM_WALL
- 930  UCLEM road emissivity                 <- EM_IMPROAD
- 931  UCLEM canyon vegetation emissivity    <- EM_PERROAD

The urban mask follows the existing class-15 field from the supplied
vegetation ancillary. Land non-urban points are written as zero; sea points are
written as the ancillary missing-data indicator.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import rasterio
from scipy.spatial import cKDTree

DEFAULT_USURF_DIR = Path("/g/data/pu02/jl8556/ancil_dataset/u-surf/USurf_1km_geotiff_v1.1")
DEFAULT_VEG = Path("/g/data/pu02/jl8556/new_ancils/qrparm.veg.frac_cci_n512e_urban")
DEFAULT_BASE = Path("/g/data/pu02/jl8556/ancils/n512/qrparm.MORUSES.morph_new")
DEFAULT_OUTPUT = Path("/g/data/pu02/jl8556/usurf_ancil/qrparm.USURF.uclem_morph_920_931")
DEFAULT_FINAL_NPZ = Path("/g/data/pu02/jl8556/usurf_ancil/qrparm.USURF.uclem_morph_920_931.fields.npz")
DEFAULT_GRID_CACHE = Path("/g/data/pu02/jl8556/usurf_ancil/qrparm_n512_class15_grid.npz")
DEFAULT_SUMMARY_JSON = Path("/g/data/pu02/jl8556/usurf_ancil/qrparm.USURF.uclem_morph_920_931.summary.json")
@dataclass(frozen=True)
class SourceSpec:
    name: str
    tif_name: str
    valid_min: float | None = None
    valid_max: float | None = None
    positive_only: bool = False


@dataclass(frozen=True)
class OutputSpec:
    stash: int
    name: str
    build: Callable[[dict[str, np.ndarray]], np.ndarray]


SOURCE_SPECS: dict[str, SourceSpec] = {
    "HT_ROOF": SourceSpec(
        name="HT_ROOF",
        tif_name="global_HT_ROOF_1km_masked_gapfilled_QC_v1.1.tif",
        positive_only=True,
    ),
    "CANYON_HWR": SourceSpec(
        name="CANYON_HWR",
        tif_name="global_CANYON_HWR_1km_masked_gapfilled_QC_v1.1.tif",
        positive_only=True,
    ),
    "WTLUNIT_ROOF": SourceSpec(
        name="WTLUNIT_ROOF",
        tif_name="global_WTLUNIT_ROOF_1km_masked_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "WTROAD_PERV": SourceSpec(
        name="WTROAD_PERV",
        tif_name="global_WTROAD_PERV_1km_masked_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "ALB_ROOF": SourceSpec(
        name="ALB_ROOF",
        tif_name="global_ALB_ROOF_1km_masked_gapfilled_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "ALB_WALL": SourceSpec(
        name="ALB_WALL",
        tif_name="global_ALB_WALL_1km_masked_gapfilled_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "ALB_IMPROAD": SourceSpec(
        name="ALB_IMPROAD",
        tif_name="global_ALB_IMPROAD_1km_masked_gapfilled_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "ALB_PERROAD": SourceSpec(
        name="ALB_PERROAD",
        tif_name="global_ALB_PERROAD_1km_masked_gapfilled_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "EM_ROOF": SourceSpec(
        name="EM_ROOF",
        tif_name="global_EM_ROOF_1km_masked_gapfilled_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "EM_WALL": SourceSpec(
        name="EM_WALL",
        tif_name="global_EM_WALL_1km_masked_gapfilled_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "EM_IMPROAD": SourceSpec(
        name="EM_IMPROAD",
        tif_name="global_EM_IMPROAD_1km_masked_gapfilled_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
    "EM_PERROAD": SourceSpec(
        name="EM_PERROAD",
        tif_name="global_EM_PERROAD_1km_masked_gapfilled_QC_v1.1.tif",
        valid_min=0.0,
        valid_max=1.0,
    ),
}

OUTPUT_SPECS: tuple[OutputSpec, ...] = (
    OutputSpec(920, "UCLEM_BUILDING_HEIGHT", lambda s: s["HT_ROOF"]),
    OutputSpec(921, "UCLEM_CANYON_HWR", lambda s: s["CANYON_HWR"]),
    OutputSpec(922, "UCLEM_WIDTH_RATIO", lambda s: np.clip(1.0 - s["WTLUNIT_ROOF"], 0.0, 1.0)),
    OutputSpec(923, "UCLEM_ROOF_ALBEDO", lambda s: s["ALB_ROOF"]),
    OutputSpec(924, "UCLEM_WALL_ALBEDO", lambda s: s["ALB_WALL"]),
    OutputSpec(925, "UCLEM_ROAD_ALBEDO", lambda s: s["ALB_IMPROAD"]),
    OutputSpec(
        926,
        "UCLEM_CANYON_VEG_FRACTION",
        lambda s: np.clip(s["WTROAD_PERV"] * (1.0 - s["WTLUNIT_ROOF"]), 0.0, 1.0),
    ),
    OutputSpec(927, "UCLEM_CANYON_VEG_ALBEDO", lambda s: s["ALB_PERROAD"]),
    OutputSpec(928, "UCLEM_ROOF_EMISSIVITY", lambda s: s["EM_ROOF"]),
    OutputSpec(929, "UCLEM_WALL_EMISSIVITY", lambda s: s["EM_WALL"]),
    OutputSpec(930, "UCLEM_ROAD_EMISSIVITY", lambda s: s["EM_IMPROAD"]),
    OutputSpec(931, "UCLEM_CANYON_VEG_EMISSIVITY", lambda s: s["EM_PERROAD"]),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usurf-dir", type=Path, default=DEFAULT_USURF_DIR, help="Directory containing U-Surf GeoTIFF inputs")
    parser.add_argument("--veg", type=Path, default=DEFAULT_VEG, help="Urban vegetation ancillary")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE, help="Base morphology ancillary")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output UCLEM ancillary")
    parser.add_argument("--grid-cache", type=Path, default=DEFAULT_GRID_CACHE, help="Cached N512 land/urban mask and grid")
    parser.add_argument("--final-npz", type=Path, default=DEFAULT_FINAL_NPZ, help="Write final 920-931 arrays to an NPZ payload")
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON, help="Write a JSON summary")
    parser.add_argument(
        "--urban-threshold",
        type=float,
        default=1.0e-12,
        help="Class-15 threshold used to mark urban points",
    )
    return parser.parse_args()


def ensure_grid_cache(
    grid_cache: Path,
    veg_path: Path,
    urban_threshold: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if not grid_cache.exists():
        raise FileNotFoundError(
            f"{grid_cache} not found. Generate it first with make_class15_grid_cache.py "
            f"under the mule environment using veg ancillary {veg_path} and threshold {urban_threshold}."
        )

    data = np.load(grid_cache)
    return data["land_mask"], data["urban_mask"], data["lon_std"], data["lat"]


def aggregate_raster_blockwise(
    raster_path: Path,
    nlat: int,
    nlon: int,
    dx: float,
    dy: float,
    band: int = 1,
    block_h: int = 512,
    block_w: int = 512,
) -> np.ndarray:
    sums = np.zeros((nlat, nlon), dtype=np.float64)
    counts = np.zeros((nlat, nlon), dtype=np.int64)
    with rasterio.open(raster_path) as ds:
        for row0 in range(0, ds.height, block_h):
            h = min(block_h, ds.height - row0)
            rows = row0 + np.arange(h, dtype=np.float64)
            ys = ds.transform.f + (rows + 0.5) * ds.transform.e
            ii = np.floor((ys + 90.0) / dy).astype(np.int64)
            lat_ok = (ii >= 0) & (ii < nlat)
            if not np.any(lat_ok):
                continue
            for col0 in range(0, ds.width, block_w):
                w = min(block_w, ds.width - col0)
                cols = col0 + np.arange(w, dtype=np.float64)
                xs = ds.transform.c + (cols + 0.5) * ds.transform.a
                lon = np.mod(xs, 360.0)
                jj = np.floor(lon / dx).astype(np.int64)
                lon_ok = (jj >= 0) & (jj < nlon)
                if not np.any(lon_ok):
                    continue
                arr = ds.read(
                    band,
                    window=rasterio.windows.Window(col0, row0, w, h),
                    masked=False,
                ).astype(np.float64, copy=False)
                finite = np.isfinite(arr)
                if not np.any(finite):
                    continue
                ii2d = np.broadcast_to(ii[:, None], (h, w))
                jj2d = np.broadcast_to(jj[None, :], (h, w))
                in_range = lat_ok[:, None] & lon_ok[None, :] & finite
                np.add.at(sums, (ii2d[in_range], jj2d[in_range]), arr[in_range])
                np.add.at(counts, (ii2d[in_range], jj2d[in_range]), 1)
    out = np.full((nlat, nlon), np.nan, dtype=np.float64)
    np.divide(sums, counts, out=out, where=counts > 0)
    return out


def is_valid_value(values: np.ndarray, spec: SourceSpec) -> np.ndarray:
    valid = np.isfinite(values)
    if spec.positive_only:
        valid &= values > 0.0
    if spec.valid_min is not None:
        valid &= values >= spec.valid_min
    if spec.valid_max is not None:
        valid &= values <= spec.valid_max
    return valid


def _unit_sphere_xyz(lat_deg: np.ndarray, lon_deg: np.ndarray) -> np.ndarray:
    lat_rad = np.deg2rad(lat_deg)
    lon_rad = np.deg2rad(lon_deg)
    cos_lat = np.cos(lat_rad)
    return np.column_stack(
        (
            cos_lat * np.cos(lon_rad),
            cos_lat * np.sin(lon_rad),
            np.sin(lat_rad),
        )
    )


def fill_urban_invalid_from_nearest_target(
    field: np.ndarray,
    urban_mask: np.ndarray,
    lon_std: np.ndarray,
    lat: np.ndarray,
    spec: SourceSpec,
) -> tuple[int, float]:
    invalid = urban_mask & (~is_valid_value(field, spec))
    if not np.any(invalid):
        return 0, 0.0

    valid = urban_mask & is_valid_value(field, spec)
    if not np.any(valid):
        raise RuntimeError(f"No valid target-grid values available for {spec.name}")

    lon2d, lat2d = np.meshgrid(lon_std, lat)
    valid_rows, valid_cols = np.where(valid)
    invalid_rows, invalid_cols = np.where(invalid)
    valid_xyz = _unit_sphere_xyz(lat2d[valid_rows, valid_cols], lon2d[valid_rows, valid_cols])
    invalid_xyz = _unit_sphere_xyz(lat2d[invalid_rows, invalid_cols], lon2d[invalid_rows, invalid_cols])

    tree = cKDTree(valid_xyz)
    chord_dist, nearest_idx = tree.query(invalid_xyz, workers=-1)
    field[invalid_rows, invalid_cols] = field[valid_rows[nearest_idx], valid_cols[nearest_idx]]

    central_angle = 2.0 * np.arcsin(np.clip(chord_dist / 2.0, 0.0, 1.0))
    max_radius_used = float(np.rad2deg(np.nanmax(central_angle))) if central_angle.size else 0.0
    return int(invalid_rows.size), max_radius_used


def build_output_field(bmdi: float, land_mask: np.ndarray, urban_mask: np.ndarray, urban_values: np.ndarray) -> np.ndarray:
    final = np.full(land_mask.shape, bmdi, dtype=np.float64)
    final[land_mask] = 0.0
    final[urban_mask] = urban_values[urban_mask]
    return final


def summarize_final_field(arr: np.ndarray, bmdi: float) -> dict[str, float | int]:
    valid = arr != bmdi
    zero = valid & (arr == 0.0)
    nonzero = valid & (arr != 0.0)
    out: dict[str, float | int] = {
        "valid": int(valid.sum()),
        "zero": int(zero.sum()),
        "nonzero": int(nonzero.sum()),
        "missing": int((~valid).sum()),
    }
    if nonzero.any():
        out["min_nonzero"] = float(arr[nonzero].min())
        out["max_nonzero"] = float(arr[nonzero].max())
        out["mean_nonzero"] = float(arr[nonzero].mean())
    else:
        out["min_nonzero"] = float("nan")
        out["max_nonzero"] = float("nan")
        out["mean_nonzero"] = float("nan")
    return out


def main() -> None:
    args = parse_args()
    land_mask, urban_mask, lon_std, lat = ensure_grid_cache(args.grid_cache, args.veg, args.urban_threshold)

    raw_fields: dict[str, np.ndarray] = {}
    source_summary: dict[str, dict[str, float | int]] = {}
    width = land_mask.shape[1]
    height = land_mask.shape[0]
    dx = float((lon_std[1] - lon_std[0]) % 360.0)
    dy = float(lat[1] - lat[0])

    for source_name, spec in SOURCE_SPECS.items():
        source_path = args.usurf_dir / spec.tif_name
        print(f"REGRID {source_name} {source_path}")
        averaged = aggregate_raster_blockwise(
            source_path,
            nlat=height,
            nlon=width,
            dx=dx,
            dy=dy,
        )
        filled_count, max_radius = fill_urban_invalid_from_nearest_target(
            averaged,
            urban_mask,
            lon_std,
            lat,
            spec,
        )
        if spec.valid_min is not None or spec.valid_max is not None:
            averaged = np.clip(
                averaged,
                -np.inf if spec.valid_min is None else spec.valid_min,
                np.inf if spec.valid_max is None else spec.valid_max,
            )
        raw_fields[source_name] = averaged
        valid = urban_mask & is_valid_value(averaged, spec)
        source_summary[source_name] = {
            "urban_valid_count": int(valid.sum()),
            "urban_invalid_count": int((urban_mask & ~valid).sum()),
            "nearest_filled_count": filled_count,
            "max_radius_used_deg": float(max_radius),
            "urban_min": float(np.nanmin(averaged[urban_mask])) if urban_mask.any() else float("nan"),
            "urban_max": float(np.nanmax(averaged[urban_mask])) if urban_mask.any() else float("nan"),
            "urban_mean": float(np.nanmean(averaged[urban_mask])) if urban_mask.any() else float("nan"),
        }

    bmdi = -1073741824.0
    final_fields: dict[int, np.ndarray] = {}
    final_summary: dict[str, dict[str, float | int]] = {}

    for spec in OUTPUT_SPECS:
        urban_values = np.asarray(spec.build(raw_fields), dtype=np.float64)
        final = build_output_field(bmdi, land_mask, urban_mask, urban_values)
        final_fields[spec.stash] = final
        final_summary[str(spec.stash)] = summarize_final_field(final, bmdi)

    args.final_npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.final_npz, **{f"stash_{stash}": data for stash, data in final_fields.items()})

    summary = {
        "base": str(args.base),
        "output": str(args.output),
        "final_npz": str(args.final_npz),
        "usurf_dir": str(args.usurf_dir),
        "veg": str(args.veg),
        "land_count": int(land_mask.sum()),
        "urban_count": int(urban_mask.sum()),
        "land_nonurban_zero_count": int((land_mask & ~urban_mask).sum()),
        "source_summary": source_summary,
        "final_summary": final_summary,
        "mapping": {
            "920": "HT_ROOF",
            "921": "CANYON_HWR",
            "922": "1 - WTLUNIT_ROOF",
            "923": "ALB_ROOF",
            "924": "ALB_WALL",
            "925": "ALB_IMPROAD",
            "926": "WTROAD_PERV * (1 - WTLUNIT_ROOF)",
            "927": "ALB_PERROAD",
            "928": "EM_ROOF",
            "929": "EM_WALL",
            "930": "EM_IMPROAD",
            "931": "EM_PERROAD",
        },
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="ascii")

    print(f"LAND_COUNT {summary['land_count']}")
    print(f"URBAN_COUNT {summary['urban_count']}")
    print(f"LAND_NONURBAN_ZERO_COUNT {summary['land_nonurban_zero_count']}")
    print(f"FINAL_NPZ {args.final_npz}")
    print(f"SUMMARY_JSON {args.summary_json}")
    for stash in sorted(final_fields):
        stats = final_summary[str(stash)]
        print(
            f"STASH {stash} NONZERO {stats['nonzero']} "
            f"MIN {stats['min_nonzero']} MAX {stats['max_nonzero']} "
            f"MEAN {stats['mean_nonzero']}"
        )


if __name__ == "__main__":
    main()
