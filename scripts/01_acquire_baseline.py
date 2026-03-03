#!/usr/bin/env python3
"""
scripts/01_acquire_baseline.py
───────────────────────────────
BATCH ACQUISITION RITUAL

Downloads the 5 clearest Sentinel-2 images per quarter for each Madurai zone.
Organizes as: data/raw/sentinel/{zone}/{date}/
Expected data volume: 50-100 GB total.

Usage:
    source venv/bin/activate
    export SENTINEL_USER=your_username
    export SENTINEL_PASS=your_password
    python scripts/01_acquire_baseline.py [--zones all] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.madurai_zones import all_zones, get_zone, ZONES
from src.data.sentinel_downloader import SentinelOracle
from src.data.footprint_utils import zone_to_wkt

logger = logging.getLogger(__name__)

# ── Quarterly intervals (avoiding monsoon peak Jun-Aug) ────────────────────────
QUARTERS = [
    ("2023-01-01", "2023-03-31", "Q1_dry"),
    ("2023-04-01", "2023-06-30", "Q2_premonsoon"),
    ("2023-09-01", "2023-11-30", "Q3_postmonsoon"),
    ("2023-12-01", "2023-12-31", "Q4_winter"),
]

IMAGES_PER_QUARTER = 5
MAX_CLOUD = 20


def acquire_zone(oracle: SentinelOracle, zone_name: str, dry_run: bool = False) -> dict:
    zone = get_zone(zone_name)
    results = {}

    for start, end, label in QUARTERS:
        try:
            products = oracle.query_zone(zone, start, end, max_cloud=MAX_CLOUD)
            sorted_p = oracle.sort_by_cloud(products)
            top = sorted_p[:IMAGES_PER_QUARTER]

            logger.info(f"  [{label}] {len(top)} products queued")

            if dry_run:
                for pid, meta in top:
                    logger.info(
                        f"    DRY-RUN | {meta.get('title', pid)[:60]}  "
                        f"cloud={meta.get('cloudcoverpercentage',0):.1f}%"
                    )
                results[label] = [str(pid) for pid, _ in top]
                continue

            downloaded = []
            for pid, meta in top:
                date_str = str(meta.get("beginposition", "unknown"))[:10].replace("-", "")
                out_dir = Path("data/raw/sentinel") / zone.name / date_str
                try:
                    safe_path = oracle.download_product(str(pid), str(out_dir))
                    # Auto-convert to GeoTIFF
                    tif_path = oracle.convert_to_geotiff(safe_path)
                    downloaded.append(str(tif_path))
                    logger.info(f"    ✅ {safe_path.name} → {tif_path.name}")
                except Exception as e:
                    logger.warning(f"    ❌ {pid}: {e}")

            results[label] = downloaded

        except Exception as e:
            logger.error(f"  [{label}] Query failed: {e}")
            results[label] = []

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch Sentinel-2 acquisition for Madurai waste zones"
    )
    parser.add_argument(
        "--zones",
        nargs="+",
        default=["all"],
        help="Zone names to acquire (default: all). "
             f"Available: {list(ZONES.keys())}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Query only, do not download",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    zone_names = list(ZONES.keys()) if args.zones == ["all"] else args.zones

    logger.info("=" * 60)
    logger.info("  SHADOW-LITTER  ::  BATCH ACQUISITION RITUAL")
    logger.info("=" * 60)
    logger.info(f"  Zones:   {zone_names}")
    logger.info(f"  Quarters: {len(QUARTERS)}")
    logger.info(f"  Images/quarter: {IMAGES_PER_QUARTER}")
    logger.info(f"  Dry run: {args.dry_run}")
    logger.info("=" * 60)

    try:
        oracle = SentinelOracle()
    except Exception as e:
        logger.error(f"Failed to connect to Copernicus Hub: {e}")
        logger.error("Set SENTINEL_USER and SENTINEL_PASS environment variables.")
        sys.exit(1)

    grand_total = 0
    for zone_name in zone_names:
        logger.info(f"\n{'─'*40}")
        logger.info(f"  ZONE: {zone_name.upper()}")
        logger.info(f"{'─'*40}")
        try:
            results = acquire_zone(oracle, zone_name, dry_run=args.dry_run)
            zone_total = sum(len(v) for v in results.values())
            grand_total += zone_total
            logger.info(f"  Zone complete: {zone_total} images acquired/queued")
        except Exception as e:
            logger.error(f"  Zone {zone_name} failed: {e}")

    logger.info(f"\n🛰️  ACQUISITION COMPLETE: {grand_total} total images")
    if not args.dry_run:
        logger.info("  Next step: python src/data/preprocess.py")


if __name__ == "__main__":
    main()
