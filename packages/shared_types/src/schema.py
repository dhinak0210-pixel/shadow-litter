# packages/shared-types/src/schema.py
# Python mirror of TypeScript schemas

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Tuple, Any
from pydantic import BaseModel, Field

# Assuming geojson-pydantic is available or using a simple Polygon model
class Polygon(BaseModel):
    type: str = "Polygon"
    coordinates: List[List[List[float]]]

class Constellation(str, Enum):
    SENTINEL_2 = "SENTINEL_2"
    LANDSAT_9 = "LANDSAT_9"
    PLANET_SCOPE = "PLANET_SCOPE"

class WasteType(str, Enum):
    FRESH_MSW = "FRESH_MSW"
    CONSTRUCTION = "CONSTRUCTION"
    CHEMICAL = "CHEMICAL"
    LEACHATE = "LEACHATE"
    LEGACY = "LEGACY"

class Detection(BaseModel):
    id: str = Field(..., description="UUID v4")
    scene_id: str
    zone_id: str
    geometry: Polygon
    center_lat: Decimal = Field(..., max_digits=10, decimal_places=8)
    center_lon: Decimal = Field(..., max_digits=11, decimal_places=8)
    area_sqm: float
    confidence: float = Field(..., ge=0, le=1)
    waste_type: WasteType
    growth_rate: Optional[float] = None
    toxicity_index: Optional[float] = Field(None, ge=0, le=10)
    first_detected_at: datetime
    last_verified_at: Optional[datetime] = None
    status: str = "NEW"
    model_version: str
    processing_pipeline: str
    municipal_ticket_id: Optional[str] = None
    alert_sent: bool = False
    ground_photos: Optional[List[str]] = None
    
    class Config:
        from_attributes = True
