"""
src/data/temporal_pairs.py
───────────────────────────
Temporal pairing ritual.
Creates (t1, t2) image pairs for change detection training.
Same zone, same seasonal window, separated by target interval.

Avoids monsoon-season pairs (June-September in Tamil Nadu) to 
reduce cloud/flood false positives.
"""
from __future__ import annotations

import csv
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Monsoon blackout months for Madurai (high cloud + water false positives)
MONSOON_MONTHS = {6, 7, 8, 9}   # June–September


def create_change_pairs(
    zone: str,
    data_dir: str = "data/raw/sentinel",
    interval_days: int = 180,
    tolerance_days: int = 30,
    output_csv: Optional[str] = None,
) -> list[dict]:
    """
    Find all valid (t1, t2) pairs for a zone.

    Args:
        zone:            Zone name (subdirectory under data_dir)
        data_dir:        Root directory for raw sentinel data
        interval_days:   Target time gap between images (default 180d = 6mo)
        tolerance_days:  Acceptable deviation from interval_days
        output_csv:      Path to save pairs CSV

    Returns:
        List of pair dicts with t1_path, t2_path, delta_days, zone
    """
    zone_dir = Path(data_dir) / zone
    if not zone_dir.exists():
        logger.warning(f"Zone directory not found: {zone_dir}")
        return []

    # Collect all GeoTIFFs in zone directory
    tif_files = sorted(zone_dir.rglob("*_stacked.tif"))
    if len(tif_files) < 2:
        logger.warning(f"[{zone}] Need ≥ 2 images, found {len(tif_files)}")
        return []

    # Parse dates from filenames (YYYYMMDD format in path)
    dated_files = []
    for f in tif_files:
        parsed = _parse_date_from_path(f)
        if parsed:
            dated_files.append((parsed, f))

    dated_files.sort(key=lambda x: x[0])
    logger.info(f"[{zone}] {len(dated_files)} dated images found")

    pairs = []
    for i, (d1, f1) in enumerate(dated_files):
        for d2, f2 in dated_files[i + 1:]:
            delta = (d2 - d1).days

            # Skip if outside tolerance window
            if abs(delta - interval_days) > tolerance_days:
                continue

            # Skip monsoon pairs
            if d1.month in MONSOON_MONTHS or d2.month in MONSOON_MONTHS:
                logger.debug(f"Skipping monsoon pair: {d1} – {d2}")
                continue

            # Prefer same-season pairs (within 45 days same month last year)
            same_season = abs(d1.month - d2.month) <= 1 or abs(d1.month - d2.month) >= 11

            pairs.append({
                "zone": zone,
                "t1_path": str(f1),
                "t2_path": str(f2),
                "t1_date": str(d1),
                "t2_date": str(d2),
                "delta_days": delta,
                "same_season": same_season,
            })

    # Sort: prefer same-season pairs first
    pairs.sort(key=lambda p: (not p["same_season"], abs(p["delta_days"] - interval_days)))
    logger.info(f"[{zone}] {len(pairs)} pairs generated")

    if output_csv:
        _write_csv(pairs, output_csv)

    return pairs


def create_all_pairs(
    zones: list[str],
    data_dir: str = "data/raw/sentinel",
    interval_days: int = 180,
    tolerance_days: int = 30,
    output_csv: str = "data/splits/temporal_pairs.csv",
) -> list[dict]:
    """
    Generate pairs for all zones and save to a single CSV.
    Target: 1000+ pairs across all zones.
    """
    all_pairs = []
    for zone in zones:
        pairs = create_change_pairs(
            zone, data_dir, interval_days, tolerance_days
        )
        all_pairs.extend(pairs)

    _write_csv(all_pairs, output_csv)
    logger.info(
        f"✅ Total pairs: {len(all_pairs)} across {len(zones)} zones → {output_csv}"
    )
    return all_pairs


def _parse_date_from_path(path: Path) -> Optional[date]:
    """Extract YYYYMMDD date from path components."""
    for part in reversed(path.parts):
        if len(part) == 8 and part.isdigit():
            try:
                return date(int(part[:4]), int(part[4:6]), int(part[6:8]))
            except ValueError:
                continue
    return None


def _write_csv(pairs: list[dict], output_csv: str) -> None:
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    if not pairs:
        return
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(pairs[0].keys()))
        writer.writeheader()
        writer.writerows(pairs)
    logger.info(f"Pairs CSV written → {output_csv}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from src.data.madurai_zones import ZONES
    all_pairs = create_all_pairs(list(ZONES.keys()))
    print(f"Generated {len(all_pairs)} temporal pairs.")
