# apps/api/src/main.py
# FastAPI with Unified Project Structure

from fastapi import FastAPI, WebSocket, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

# New imports for model inference and Prisma client
import torch
from src.models.siamese_unet import ShadowLitterNet
from prisma_python import Prisma


from packages.ai_engine.src.shadow_litter_ai.geo_oracle import global_oracle
from apps.api.src.civic_loop import router as civic_router

# Global instances (will be initialized in lifespan)
prisma: Prisma = None  # type: ignore
model: ShadowLitterNet = None  # type: ignore

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 API starting up...")
    # Initialize Prisma client
    global prisma, model
    prisma = Prisma()
    await prisma.connect()

    # Seed placeholder data for foreign keys
    try:
        if not await prisma.zone.find_unique(where={"id": "placeholder_zone"}):
            await prisma.zone.create(data={
                "id": "placeholder_zone",
                "name": "Madurai Central",
                "nameTamil": "மதுரை மத்தி",
                "centerLat": 9.9252,
                "centerLon": 78.1198,
                "radiusM": 5000,
                "riskLevel": "high",
                "municipalWard": "42",
                "policeStation": "B1",
                "estimatedPopulation": 50000
            })
        if not await prisma.satellitescene.find_unique(where={"id": "placeholder_scene"}):
            await prisma.satellitescene.create(data={
                "id": "placeholder_scene",
                "constellation": "Sentinel-2",
                "satelliteId": "S2A",
                "acquisitionTime": datetime.now(),
                "cloudCover": 0.0,
                "bbox": json.dumps([78.0, 9.8, 78.2, 10.0]),
                "resolution": 10,
                "sizeBytes": 1024 * 1024,
                "bands": ["B02", "B03", "B04", "B08", "B11", "B12"]
            })
    except Exception as e:
        print(f"⚠️ Seeding warning: {e}")

    # Load the trained model
    model = ShadowLitterNet()
    checkpoint = torch.load("models/final/siamese_best.pth", map_location=torch.device('cpu'), weights_only=False)
    model.load_state_dict(checkpoint['model'])
    model.eval()
    print("✅ Model and Prisma client initialized.")
    yield
    # Shutdown
    print("🛑 API shutting down...")
    await prisma.disconnect()


app = FastAPI(
    title="Shadow Litter Unified API",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(civic_router)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "gpu": torch.cuda.is_available(),
        "model_loaded": model is not None,
        "prisma_connected": prisma is not None,
    }

@app.post("/api/detect")
async def create_detection(request: dict, background_tasks: BackgroundTasks):
    """Accepts a detection request with pre/post image URLs, runs inference, stores result, and returns detection data."""
    pre_url = request.get("pre_image_url")
    post_url = request.get("post_image_url")
    if not pre_url or not post_url:
        raise HTTPException(status_code=400, detail="pre_image_url and post_image_url are required")

    job_id = str(uuid.uuid4())

    async def process_detection(job_id: str, pre_url: str, post_url: str):
        # Simple download using aiohttp
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(pre_url) as resp:
                pre_bytes = await resp.read()
            async with session.get(post_url) as resp:
                post_bytes = await resp.read()
        # Convert bytes to torch tensors (placeholder: random tensor)
        # In real implementation, decode image bytes to tensors
        # Model expects 6 channels (Sentinel-2 bands)
        pre_tensor = torch.randn(6, 256, 256)
        post_tensor = torch.randn(6, 256, 256)
        with torch.no_grad():
            output = model(pre_tensor.unsqueeze(0), post_tensor.unsqueeze(0))
        # Dummy post-processing to create a detection record
        detection = {
            "id": job_id,
            "confidence": float(output.mean().item()),
            "area_sqm": 500,
            "wasteType": "unknown",
            "geometry": {"type": "Polygon", "coordinates": []},
        }
        # Persist to DB via Prisma
        await prisma.detection.create(
            data={
                "id": detection["id"],
                "sceneId": "placeholder_scene",
                "zoneId": "placeholder_zone",
                "geometry": json.dumps(detection["geometry"]),
                "centerLat": 0.0,
                "centerLon": 0.0,
                "areaSqm": detection["area_sqm"],
                "confidence": detection["confidence"],
                "wasteType": detection["wasteType"],
                "modelVersion": "v1",
                "processingPipeline": "shadow_litter",
            }
        )
        return detection

    background_tasks.add_task(process_detection, job_id, pre_url, post_url)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/detections")
async def list_detections(zone_id: Optional[str] = None):
    return {"items": [], "total": 0}

@app.get("/api/zones/{zone_id}/forecast")
async def get_zone_forecast(zone_id: str):
    return {
        "zone_id": zone_id,
        "risk_forecast": [0.1, 0.2, 0.5],
        "recommended_actions": ["Increased patrol in Sector 4"]
    }

@app.get("/api/zones/search/{query}")
async def search_global_zone(query: str, radius_km: float = 5.0):
    """
    Translates any global city/region into orbital coordinates.
    """
    result = global_oracle.resolve_target(query, radius_km)
    if not result:
        raise HTTPException(status_code=404, detail="Location could not be resolved.")
    return result

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    import random
    types = ['fresh_dump', 'construction', 'chemical', 'leachate']
    count = 100
    try:
        while True:
            await asyncio.sleep(6) # Orbital sweep interval
            det = {
               "id": count,
               "position": [random.uniform(-15, 15), 2, random.uniform(-15, 15)],
               "type": random.choice(types),
               "area_sqm": random.randint(100, 2500),
               "confidence": round(random.uniform(85.0, 99.9), 1),
            }
            await websocket.send_json({"type": "DETECTION_CREATED", "payload": det})
            count += 1
    except Exception as e:
        print(f"WS Error: {e}")
