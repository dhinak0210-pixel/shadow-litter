"""
scripts/populate_demo_data.py
──────────────────────────────
Simulation engine for shadow-litter.
Populates the database with 24 realistic "detected" dump sites across Madurai
to showcase the dashboard's temporal and spatial capabilities.
"""
from __future__ import annotations
import random
from datetime import datetime, timedelta
from src.agent.database import DumpArchive

ZONES = [
    "vaigai_riverbed", "perungudi_lake", "thiruparankundram_quarries",
    "mattuthavani_periphery", "alagar_koil_outskirts"
]

DUMP_TYPES = ["fresh_dump", "construction_debris", "leachate", "unknown"]
WARDS = [str(i) for i in range(1, 101)]

def populate():
    db = DumpArchive()
    print("Populating Shadow Litter demo data...")
    
    # 1. Clear existing for a fresh demo (Optional)
    # db.conn.execute("DELETE FROM detections")
    # db.conn.execute("DELETE FROM dumps")
    # db.conn.commit()

    base_lat, base_lon = 9.9252, 78.1198
    
    for i in range(24):
        # Semi-random coords around Madurai (+/- 0.05 deg)
        lat = base_lat + (random.random() - 0.5) * 0.1
        lon = base_lon + (random.random() - 0.5) * 0.1
        
        zone = random.choice(ZONES)
        area = random.uniform(200, 5000)
        conf = random.uniform(0.65, 0.98)
        dtype = random.choice(DUMP_TYPES)
        ward = random.choice(WARDS)
        
        # Detection date: spread over last 30 days
        days_ago = random.randint(1, 30)
        dt = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
        
        # Log it
        dump_id = db.log_detection(
            zone=zone,
            lat=lat,
            lon=lon,
            confidence=conf,
            area_sqm=area,
            dump_type=dtype,
            ward=ward
        )
        
        # Add a few verifications
        if random.random() > 0.4:
            db.add_verification(dump_id, f"bot_{i}", random.choice(["yes", "yes", "no", "unsure"]))
            
    print(f"✅ Successfully seeded 24 sites into {db.stats()}")
    db.close()

if __name__ == "__main__":
    populate()
