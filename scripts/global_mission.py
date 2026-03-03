import argparse
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from packages.ai_engine.src.shadow_litter_ai.geo_oracle import global_oracle
from src.satellite.live_stac_connection import LiveSatelliteConnector

async def global_scan(target_name: str, radius_km: float):
    print(f"🌍 INITIATING GLOBAL NORMALIZATION PROTOCOL")
    print("──────────────────────────────────────────────")
    print(f"📡 Target Designated: {target_name}")
    print(f"📏 Search Radius: {radius_km} km")
    
    # 1. Resolve global coordinates
    resolved_target = global_oracle.resolve_target(target_name, radius_km)
    
    if not resolved_target:
        print(f"❌ Failed to locate {target_name}. Aborting mission.")
        return
        
    print("\n✅ GLOBAL COORDINATES RESOLVED:")
    print(f"   Matches: {resolved_target['display_name']}")
    print(f"   Center: {resolved_target['center_lat']:.5f}°N, {resolved_target['center_lon']:.5f}°E")
    print(f"   UTM Zone: {resolved_target['utm_zone']} ({resolved_target['epsg_code']})")
    
    # 2. Query Sentinel-2 Coverage for this region
    connector = LiveSatelliteConnector()
    print(f"\n📡 SCANNING ORBITAL COVERAGE (Sentinel-2 L2A via AWS Open Data)...")
    
    scenes = await connector.query_live_scenes(
        lat=resolved_target['center_lat'],
        lon=resolved_target['center_lon'],
        radius_m=resolved_target['radius_m'],
        max_cloud=15.0
    )
    
    if not scenes:
        print("⚠️  No recent clear sky coverage found for this region.")
        return
        
    print(f"✅ SATELLITE TELEMETRY LINKED: {len(scenes)} cloud-free scenes found.")
    
    for i, s in enumerate(scenes[:5]):
        print(f"   [{i+1}] {s['Name']} | {s['ContentDate']['Start'][:10]}")
        
    print("\n🧠 THE AI ENGINE IS READY TO INGEST DATA FOR THIS GRID.")
    print("──────────────────────────────────────────────")
    print("🌍 ORBITAL TARGETING COMPLETE.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shadow Litter Global Targeter")
    parser.add_argument("city", type=str, nargs="+", help="City or region name (e.g., 'Paris', 'Bogota Colombia')")
    parser.add_argument("--radius", type=float, default=5.0, help="Search radius in kilometers")
    
    args = parser.parse_args()
    target_city = " ".join(args.city)
    
    asyncio.run(global_scan(target_city, args.radius))
