# REPLICATION.md — shadow-litter
## How to Deploy in Another City

**shadow-litter** can be replicated for any city in ~1 hour of setup using **The Real Satellite Protocol**.

### Prerequisites
- Python 3.12+, 16GB RAM (for model fine-tuning), Internet connection
- **ESA Copernicus Account**: [Register here](https://dataspace.copernicus.eu/)
- **GEE Project ID**: [Register Google Earth Engine](https://code.earthengine.google.com/register)

### Step 1 — Fork and Clone
```bash
git clone https://github.com/your-org/shadow-litter.git
cd shadow-litter && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Step 2 — Credentials Setup
Edit `configs/default.yaml`:
```yaml
copernicus_user: "your.email@example.com"
copernicus_pass: "your_password"
gee_project_id: "your-gee-project-id"
```

### Step 3 — Define Your Monitoring Zones
Edit `src/data/madurai_zones.py` (rename or add your city):
```python
def all_zones():
    return [
        MonitoringZone(name="ZoneA", coords=(LAT, LON), radius=5000),
        # ...
    ]
```

### Step 4 — The First Scan (Data Acquisition)
Verify your orbital connection:
```bash
export PYTHONPATH=$PYTHONPATH:.
python scripts/verify_copernicus.py
python scripts/acquire_data.py
```

### Step 5 — Label Real Ground Truth
If you have local knowledge of existing dumps, use the labeling tool:
```bash
python src/annotation/real_labeling_system.py --image data/processed/your_image.tif
```

### Step 6 — Fine-tune Prithvi-2.0
Train the NASA foundation model on your city's specific spectral patterns:
```bash
python src/training/real_finetuner.py
```

### Step 7 — Launch Civic Dashboard
```bash
streamlit run app/dashboard.py
```

### Step 8 — Autonomous Deployment (Docker)
Build and run the full stack:
```bash
docker-compose up --build
```

### Cost: $0
All satellite data is open (Sentinel-2). The Prithvi model is open-source. The compute runs on standard hardware or free cloud tiers.

---
*Open an issue or PR to add your city to the list.*
