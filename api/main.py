from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
from datetime import datetime

from agent.core_agent import ShadowLitterAgent

app = FastAPI(title="Shadow Litter Intelligence API")

# CORS for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DetectionRequest(BaseModel):
    lat: float
    lon: float
    radius_meters: int = 1000
    start_date: str
    end_date: str

class DetectionResponse(BaseModel):
    id: str
    confidence: float
    area_sqm: float
    first_detected: str
    growth_rate: Optional[float]
    geometry: dict

# Global agent instance
agent = None

@app.on_event("startup")
async def load_model():
    global agent
    agent = ShadowLitterAgent(
        model_path="weights/shadow-litter-best.ckpt",
        config_path="config/madurai.json"
    )

@app.get("/")
async def root():
    return {"status": "Shadow Litter Intelligence Active", "version": "1.0.0"}

@app.post("/analyze", response_model=List[DetectionResponse])
async def analyze_region(request: DetectionRequest):
    """
    On-demand analysis of specific region.
    Real-time inference on latest available satellite imagery.
    """
    # Search for imagery
    scenes = agent.feed.search_temporal_stack(
        request.start_date, 
        request.end_date,
        cloud_cover=15.0
    )
    
    if len(scenes) < 2:
        raise HTTPException(400, "Insufficient imagery for change detection")
        
    # Run detection
    detections = []
    for i in range(len(scenes)-1):
        before = scenes[i]
        after = scenes[i+1]
        
        # Process pair
        mask = agent._verify_temporal_consistency(
            after, 
            (datetime.fromisoformat(before['datetime']), 
             datetime.fromisoformat(before['datetime']))
        )
        
        if mask is not None:
            dumps = agent._extract_dump_polygons(mask, after)
            detections.extend(dumps)
            
    return [DetectionResponse(**d) for d in detections]

@app.get("/heatmap")
async def get_heatmap(ward: Optional[str] = None):
    """
    Get current dump heatmap for dashboard.
    Returns GeoJSON with clustering.
    """
    # Query from database/Redis cache
    detections = json.loads(agent.redis_client.get('current_detections') or '[]')
    
    if ward:
        detections = [d for d in detections if d['ward'] == ward]
        
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": d['geometry'].__geo_interface__,
                "properties": {
                    "confidence": d['confidence'],
                    "area": d['area_sqm'],
                    "ward": d['ward']
                }
            }
            for d in detections
        ]
    }

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket for real-time detection streaming.
    Pushes new detections as they are processed.
    """
    await websocket.accept()
    try:
        while True:
            # Check for new detections in Redis pub/sub
            message = agent.redis_client.pubsub().get_message()
            if message and message['type'] == 'message':
                await websocket.send_json(json.loads(message['data']))
            await asyncio.sleep(1)
    except Exception as e:
        await websocket.close()

@app.post("/trigger-scan")
async def manual_scan(background_tasks: BackgroundTasks):
    """
    Manually trigger weekly scan ritual.
    """
    from agent.core_agent import run_weekly_scan
    task = run_weekly_scan.delay()
    return {"task_id": task.id, "status": "Scan initiated"}
