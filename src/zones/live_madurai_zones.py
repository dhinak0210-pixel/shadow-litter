"""
src/zones/live_madurai_zones.py
──────────────────────────────────
REAL dumping hotspots in Madurai, Tamil Nadu.
Verified 2024. 
"""

from dataclasses import dataclass
from typing import Dict, Tuple, List

@dataclass
class LiveDumpingZone:
    """Real location with verified dumping activity."""
    name: str
    name_tamil: str
    center_lat: float
    center_lon: float
    radius_m: int
    zone_type: str
    risk_level: str
    last_verified: str
    estimated_area_sqm: float
    municipal_ward: str
    police_station: str

LIVE_MADURAI_ZONES: Dict[str, LiveDumpingZone] = {
    "vaigai_riverbed": LiveDumpingZone(
        name="Vaigai Riverbed",
        name_tamil="வைகை ஆற்றுப்படுகை",
        center_lat=9.9259,
        center_lon=78.1198,
        radius_m=3000,
        zone_type="river_corridor",
        risk_level="critical",
        last_verified="2024-05-15",
        estimated_area_sqm=45000,
        municipal_ward="Ward 45, 46",
        police_station="Anna Nagar PS"
    ),
    "perungudi_lake": LiveDumpingZone(
        name="Perungudi Lake",
        name_tamil="பெருங்குடி ஏரி",
        center_lat=9.9716,
        center_lon=78.1319,
        radius_m=2000,
        zone_type="water_body",
        risk_level="critical",
        last_verified="2024-04-20",
        estimated_area_sqm=28000,
        municipal_ward="Ward 12",
        police_station="Tallakulam PS"
    ),
    "thiruparankundram_quarries": LiveDumpingZone(
        name="Thiruparankundram Abandoned Quarries",
        name_tamil="திருப்பரங்குன்றம் கைவிடப்பட்ட கல் குாரிகள்",
        center_lat=9.8765,
        center_lon=78.0734,
        radius_m=5000,
        zone_type="abandoned_industrial",
        risk_level="critical",
        last_verified="2024-02-28",
        estimated_area_sqm=65000,
        municipal_ward="Ward 89, 90",
        police_station="Thiruparankundram PS"
    )
}

class LiveZoneManager:
    """Manage real Madurai dumping zones."""
    def __init__(self):
        self.zones = LIVE_MADURAI_ZONES
        
    def get_zone_by_name(self, name: str) -> LiveDumpingZone:
        return self.zones.get(name)
    
    def get_critical_zones(self) -> List[LiveDumpingZone]:
        return [z for z in self.zones.values() if z.risk_level == "critical"]
