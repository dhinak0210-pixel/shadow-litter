# Shadow Litter: Live Orbital Feed & Autonomous Operations 🛰️⚡🤖
"Beyond the archive. Live photons. Sub-second truth."

---

## 🏗️ Architecture Overview

The **Streaming & Autonomy Suite** converts the Shadow Litter model from a batch processor into a real-time digital sentry.

### 1. Multi-Constellation Engine (`src/streaming/live_orbital_feed.py`)
- **Direct Broadcast**: Connects to ESA (Sentinel-2) and Planet Labs streams.
- **Protocol**: COG (Cloud Optimized GeoTIFF) streaming via HTTP range requests—reading pixels while the satellite is still downlinking.
- **Coverage**: Madurai is monitored by a fusion of 10m (Sentinel), 30m (Landsat), and 3.7m (PlanetScope) datasets.

### 2. Sub-Second Pipeline (`src/streaming/realtime_tile_processor.py`)
- **GPU Batching**: Tiles are queued and processed in dynamic batches to maximize throughput.
- **Latency**: Targeted at **< 500ms** from tile reception to detection.
- **Change Detection**: Real-time temporal comparison against cached historical shards.

### 3. 30-Day Forecast Engine (`src/prediction/orbital_forecast_engine.py`)
- **Orbital Propagation**: Uses TLE (Two-Line Element) data and SGP4 to predict exact overpass times for Madurai.
- **Risk Modeling**: Predicts high-dumping periods based on local festival calendars and market cycles.
- **Cloud Masking**: Probabilistic cloud forecasting determines the optimal acquisition windows.

### 4. Self-Driving Satellite Agent (`src/autonomous/self_driving_satellite_agent.py`)
- **The Brain**: An autonomous orchestrator that makes operational decisions every second.
- **Emergency Tasking**: Automatically requests high-resolution SkySat imagery if critical anomalies are detected in low-res streams.
- **Self-Maintenance**: Triggers automated retraining if the confidence of live detections drops below baseline.

---

## 🚀 Deployment

To start the autonomous orbital sentry:
```bash
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
python src/autonomous/self_driving_satellite_agent.py
```

---
*Autonomous orbital intelligence for the common good. Built for Madurai.*
