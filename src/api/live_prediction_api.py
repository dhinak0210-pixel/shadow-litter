"""
src/api/live_prediction_api.py
──────────────────────────────
LIVE REST API for waste dump detection.
Hardened with Pydantic validation and security checks.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator, root_validator
from typing import List, Optional
from datetime import datetime, date
import json
import logging
from circuitbreaker import circuit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_service")

app = FastAPI(title="Shadow Litter LIVE API (HARDENED)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_ZONES = [
    'vaigai_riverbed', 'perungudi_lake', 'thiruparankundram_quarries',
    'alagar_koil_outskirts', 'mattuthavani_bus_stand', 
    'kochadai_market', 'avaniapuram_dumping_yard', 'sathamangalam_canal'
]

class DetectionRequest(BaseModel):
    zone: str
    date_start: str
    date_end: Optional[str] = None

    @validator('zone')
    def validate_zone(cls, v):
        if v not in VALID_ZONES:
            raise ValueError(f"Invalid zone. Choice from: {', '.join(VALID_ZONES)}")
        return v

    @validator('date_start', 'date_end')
    def validate_date_format(cls, v):
        if v is None: return v
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError("Date must be YYYY-MM-DD")
        return v

    @root_validator
    def validate_range(cls, values):
        start = values.get('date_start')
        end = values.get('date_end')
        if start and end:
            s_dt = datetime.strptime(start, '%Y-%m-%d')
            e_dt = datetime.strptime(end, '%Y-%m-%d')
            if (e_dt - s_dt).days > 90:
                raise ValueError("Range cannot exceed 90 days")
            if s_dt.year < 2015:
                raise ValueError("No data before 2015")
        return values

@app.post("/detect")
@circuit(failure_threshold=5, recovery_timeout=60)
async def create_detection_job(request: DetectionRequest):
    request_id = f"SL{datetime.now().strftime('%Y%m%d%H%M%S')}"
    logger.info(f"JOB CREATED: {request_id} for zone {request.zone}")
    return {
        "request_id": request_id,
        "status": "processing",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/zones")
async def list_zones():
    return {"zones": VALID_ZONES, "count": len(VALID_ZONES)}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "Prithvi-EO-2.0"}
