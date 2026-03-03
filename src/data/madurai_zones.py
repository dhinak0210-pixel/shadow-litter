"""
src/data/madurai_zones.py
─────────────────────────
The hunting grounds. Five zones of maximum waste risk across Madurai district.
Each zone carries coordinates, radius, ecological context, and ward metadata.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

# ── Zone registry ─────────────────────────────────────────────────────────────

ZONES: dict[str, dict] = {
    "vaigai_riverbed": {
        "coords": (9.9259, 78.1198),
        "radius": 2000,          # meters
        "why": "historical_dumping_seasonal_visibility",
        "ward": "47",
        "water_body": "Vaigai River",
        "risk_level": "critical",
        "notes": "Monsoon recession exposes buried waste. Highly visible in Jan-Mar.",
    },
    "perungudi_lake": {
        "coords": (9.9716, 78.1319),
        "radius": 1500,
        "why": "water_encroachment",
        "ward": "12",
        "water_body": "Perungudi Lake",
        "risk_level": "high",
        "notes": "Encroachment from eastern fringes. Leachate risk to groundwater.",
    },
    "alagar_koil_outskirts": {
        "coords": (10.0833, 78.2167),
        "radius": 3000,
        "why": "tourism_plus_unregulated_growth",
        "ward": None,            # peri-urban, no ward assignment
        "water_body": None,
        "risk_level": "medium",
        "notes": "Temple tourism corridor. Seasonal plastic surge during festival months.",
    },
    "mattuthavani_periphery": {
        "coords": (9.9566, 78.1442),
        "radius": 2500,
        "why": "high_traffic_informal_settlements",
        "ward": "33",
        "water_body": None,
        "risk_level": "high",
        "notes": "Bus terminus overflow. Construction debris + household mixed dumps.",
    },
    "thiruparankundram_quarries": {
        "coords": (9.8765, 78.0734),
        "radius": 4000,
        "why": "abandoned_pits_dumps",
        "ward": "5",
        "water_body": None,
        "risk_level": "critical",
        "notes": "Ex-quarry pits used as landfills. Deep accumulation, hard to clear.",
    },
}


@dataclass
class Zone:
    """Structured representation of a monitoring zone."""
    name: str
    lat: float
    lon: float
    radius_m: float
    why: str
    risk_level: str
    ward: Optional[str] = None
    water_body: Optional[str] = None
    notes: str = ""

    @property
    def coords(self) -> tuple[float, float]:
        return (self.lat, self.lon)

    @property
    def bbox_deg(self, buffer_factor: float = 1.2) -> tuple[float, float, float, float]:
        """Approximate bounding box in degrees (south, north, west, east)."""
        margin = (self.radius_m * buffer_factor) / 111_000  # ≈ degrees per meter at equator
        return (
            self.lat - margin,
            self.lat + margin,
            self.lon - margin,
            self.lon + margin,
        )


def get_zone(name: str) -> Zone:
    if name not in ZONES:
        raise KeyError(f"Unknown zone '{name}'. Available: {list(ZONES.keys())}")
    z = ZONES[name]
    lat, lon = z["coords"]
    return Zone(
        name=name,
        lat=lat,
        lon=lon,
        radius_m=z["radius"],
        why=z["why"],
        risk_level=z["risk_level"],
        ward=z.get("ward"),
        water_body=z.get("water_body"),
        notes=z.get("notes", ""),
    )


def all_zones() -> list[Zone]:
    return [get_zone(name) for name in ZONES]


if __name__ == "__main__":
    for zone in all_zones():
        print(f"[{zone.risk_level.upper():8s}] {zone.name:35s}  "
              f"({zone.lat:.4f}°N, {zone.lon:.4f}°E)  r={zone.radius_m}m")
