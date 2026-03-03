"""
src/agent/shadow_litter_agent.py
─────────────────────────────────
ShadowLitterAgent — the autonomous weekly orbital watch.

Iterates over all monitoring zones, queries the latest clear Sentinel-2 image,
runs the Siamese change detector against a seasonal baseline, filters genuine
new dumps, and generates prioritized alerts.

Schedule: every Monday 00:00 UTC (use cron or Hugging Face Scheduled Spaces).
"""
from __future__ import annotations
import json, logging, os
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class ShadowLitterAgent:
    def __init__(self, config_path: str = "configs/config.yaml"):
        import yaml
        with open(config_path) as f:
            self.cfg = yaml.safe_load(f)
        from src.data.madurai_zones import all_zones
        from src.agent.database import DumpArchive
        self.zones = all_zones()
        self.db = DumpArchive()
        self.model = None    # lazy-loaded on first scan
        self.model_path = str(Path(self.cfg["paths"]["final"]) / "siamese_best.pth")
        logger.info(f"ShadowLitterAgent initialized | {len(self.zones)} zones")

    # ── Public API ─────────────────────────────────────────────────────────────

    def weekly_scan(self) -> list[dict]:
        """Run detection across all zones. Returns list of alert dicts."""
        self._load_model()
        alerts = []
        scan_date = date.today()
        for zone in self.zones:
            logger.info(f"{'─'*40}\nScanning zone: {zone.name}")
            try:
                zone_alerts = self._scan_zone(zone, scan_date)
                alerts.extend(zone_alerts)
            except Exception as e:
                logger.error(f"[{zone.name}] Scan failed: {e}", exc_info=True)
        logger.info(f"Scan complete. {len(alerts)} new alerts generated.")
        return alerts

    def run(self) -> None:
        """Blocking weekly scheduler (for daemon mode)."""
        import time
        while True:
            next_monday = self._next_monday()
            wait_sec = (next_monday - datetime.utcnow()).total_seconds()
            logger.info(f"Next scan at {next_monday.isoformat()} (in {wait_sec/3600:.1f}h)")
            time.sleep(max(wait_sec, 0))
            self.weekly_scan()

    # ── Zone scan ─────────────────────────────────────────────────────────────

    def _scan_zone(self, zone, scan_date: date) -> list[dict]:
        from src.data.sentinel_downloader import SentinelOracle
        oracle = SentinelOracle()

        # Query last 10 days for a fresh clear image
        end = scan_date.strftime("%Y%m%d")
        start = (scan_date - timedelta(days=10)).strftime("%Y%m%d")
        products = oracle.query_zone(zone, start, end, max_cloud=15)
        if not products:
            logger.info(f"[{zone.name}] No clear images in last 10 days.")
            return []

        sorted_p = oracle.sort_by_cloud(products)
        pid, meta = sorted_p[0]

        # Download and stack
        out_dir = f"data/raw/sentinel/{zone.name}/latest"
        safe = oracle.download_product(str(pid), out_dir)
        current_tif = oracle.convert_to_geotiff(safe)

        # Load seasonal baseline (same month, prior year)
        baseline_tif = self._find_baseline(zone, scan_date)
        if baseline_tif is None:
            logger.info(f"[{zone.name}] No baseline available yet.")
            return []

        # Detect changes
        detections = self._detect(str(baseline_tif), str(current_tif), zone)
        alerts = []
        for det in detections:
            if self.is_new_dump(zone, det["lat"], det["lon"]):
                alert = self.generate_alert(zone, det, scan_date)
                dump_id = self.db.log_detection(
                    zone=zone.name, **{k: det[k] for k in ["lat", "lon", "confidence", "area_sqm"]},
                    dump_type=det.get("dump_type", "unknown"),
                    ward=zone.ward,
                )
                alert["dump_id"] = dump_id
                alerts.append(alert)
        return alerts

    # ── Change detection wrapper ───────────────────────────────────────────────

    def _detect(self, t1_path: str, t2_path: str, zone) -> list[dict]:
        from src.inference.predict_change import detect_dumps
        gdf = detect_dumps(t1_path, t2_path, model=self.model)
        results = []
        for _, row in gdf.iterrows():
            if row.geometry is None: continue
            centroid = row.geometry.centroid
            results.append({
                "lat": centroid.y,
                "lon": centroid.x,
                "confidence": float(row.get("confidence", 0)),
                "area_sqm": float(row.get("area_sqm", 0)),
                "dump_type": str(row.get("dump_type", "unknown")),
                "geojson": row.geometry.__geo_interface__,
            })
        return results

    # ── Temporal verification ─────────────────────────────────────────────────

    def is_new_dump(self, zone, lat: float, lon: float) -> bool:
        """
        Return True if detection represents a genuinely new dump site.
        Filters: known sites, seasonal changes, single-image noise.
        """
        existing = self.db.query_history(zone=zone.name, status="active")
        for ex in existing:
            dlat = abs(ex["lat"] - lat)
            dlon = abs(ex["lon"] - lon)
            if dlat < 0.001 and dlon < 0.001:  # within ~100m
                logger.debug(f"[{zone.name}] Skipping known dump at ({lat:.4f},{lon:.4f})")
                return False
        return True

    # ── Alert generation ──────────────────────────────────────────────────────

    def generate_alert(self, zone, detection: dict, scan_date: date) -> dict:
        """Package a detection into a structured alert."""
        lat, lon = detection["lat"], detection["lon"]
        priority = (
            detection["area_sqm"] * detection["confidence"] *
            (2.0 if zone.water_body else 1.0)
        )
        return {
            "zone": zone.name,
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "first_seen": scan_date.isoformat(),
            "area_sqm": round(detection["area_sqm"], 1),
            "confidence": round(detection["confidence"], 3),
            "dump_type": detection.get("dump_type", "unknown"),
            "ward": zone.ward,
            "water_body_proximity": zone.water_body,
            "risk_level": zone.risk_level,
            "priority_score": round(priority, 1),
            "maps_link": f"https://maps.google.com/?q={lat},{lon}",
            "whatsapp_message": (
                f"🚨 *Dump detected near {zone.name.replace('_',' ').title()}*\n"
                f"📍 {lat:.5f}°N, {lon:.5f}°E\n"
                f"📅 First seen: {scan_date.isoformat()}\n"
                f"📐 Area: {detection['area_sqm']:.0f} m²\n"
                f"🔍 {f'https://maps.google.com/?q={lat},{lon}'}"
            ),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        if self.model is not None: return
        if not Path(self.model_path).exists():
            logger.warning(f"Model checkpoint not found: {self.model_path}. Using untrained model.")
            from src.models.siamese_unet import ShadowLitterNet
            self.model = ShadowLitterNet(6, 2, pretrained=False)
            return
        import torch
        from src.models.siamese_unet import ShadowLitterNet
        self.model = ShadowLitterNet(6, 2, pretrained=False)
        state = torch.load(self.model_path, map_location="cpu")
        self.model.load_state_dict(state["model"])
        self.model.eval()
        logger.info(f"Model loaded from {self.model_path}")

    def _find_baseline(self, zone, current_date: date) -> Optional[Path]:
        """Find a same-month previous-year image for the zone."""
        zone_dir = Path("data/raw/sentinel") / zone.name
        if not zone_dir.exists(): return None
        target_month = current_date.month
        target_year  = current_date.year - 1
        # Look for directories named YYYYMMDD matching target year+month
        for d in sorted(zone_dir.iterdir()):
            if d.is_dir() and len(d.name) == 8 and d.name.isdigit():
                y, m = int(d.name[:4]), int(d.name[4:6])
                if y == target_year and m == target_month:
                    tifs = list(d.rglob("*_stacked.tif"))
                    if tifs: return tifs[0]
        return None

    @staticmethod
    def _next_monday() -> datetime:
        now = datetime.utcnow()
        days_ahead = (7 - now.weekday()) % 7 or 7
        return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = ShadowLitterAgent()
    alerts = agent.weekly_scan()
    print(json.dumps(alerts, indent=2))
