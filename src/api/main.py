"""
src/api/main.py
────────────────
shadow-litter :: Production API Gateway.
Exposes waste detection intelligence to mobile apps, ward dashboards, and external partners.
"""
from __future__ import annotations
from fastapi import FastAPI, Depends, HTTPException, Query, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json
import shutil
from pathlib import Path

from src.agent.database import DumpArchive

# Setup storage
UPLOAD_DIR = Path("data/raw/field_photos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="shadow-litter API",
    description="Autonomous Orbital Intelligence for Madurai Waste Detection",
    version="1.0.0"
)

# Enable CORS for frontend/mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class DumpResponse(BaseModel):
    id: int
    zone: str
    lat: float
    lon: float
    first_seen: str
    area_sqm: float
    status: str
    dump_type: str
    ward: Optional[str] = None

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["General"])
async def root():
    return {"status": "operational", "vessel": "shadow-litter", "city": "Madurai"}

@app.get("/api/v1/dumps", response_model=List[DumpResponse], tags=["Detections"])
async def get_dumps(
    zone: Optional[str] = None,
    status: str = "active",
    since: Optional[str] = None,
    limit: int = 100
):
    with DumpArchive() as db:
        results = db.query_history(zone=zone, status=status, since=since, limit=limit)
    return results

@app.get("/api/v1/dumps/{dump_id}", response_model=DumpResponse, tags=["Detections"])
async def get_dump_detail(dump_id: int):
    with DumpArchive() as db:
        # Simple manual query for detail
        row = db.conn.execute("SELECT * FROM dumps WHERE id = ?", (dump_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dump site not found")
        return dict(row)

@app.get("/api/v1/dumps/{dump_id}/timeline", tags=["Detections"])
async def get_dump_timeline(dump_id: int):
    with DumpArchive() as db:
        return db.get_dump_timeline(dump_id)

@app.get("/api/v1/stats", tags=["Analytics"])
async def get_system_stats():
    with DumpArchive() as db:
        return db.stats()

@app.post("/api/v1/verify/{dump_id}", tags=["Crowd Verification"])
async def submit_verification(
    dump_id: int, 
    user_id: str, 
    vote: str, 
    comment: str = "",
    photo: Optional[UploadFile] = File(None)
):
    if vote not in ["yes", "no", "unsure"]:
        raise HTTPException(status_code=400, detail="Invalid vote")
    
    photo_path = None
    if photo:
        ext = photo.filename.split(".")[-1]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dump_{dump_id}_{timestamp}.{ext}"
        target_path = UPLOAD_DIR / filename
        with target_path.open("wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        photo_path = str(target_path)

    with DumpArchive() as db:
        db.add_verification(dump_id, user_id, vote, comment)
        # Record photo path in detections (as additional evidence)
        if photo_path:
            db.conn.execute(
                "UPDATE detections SET image_path = ? WHERE dump_id = ? ORDER BY detected_at DESC LIMIT 1",
                (photo_path, dump_id)
            )
            db.conn.commit()
            
    return {"status": "success", "message": "Verification and photo recorded", "photo": photo_path}

# Serve field photos for the dashboard to see
app.mount("/field_photos", StaticFiles(directory=str(UPLOAD_DIR)), name="field_photos")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
