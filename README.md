# 🛰️ Shadow Litter: Orbital Intelligence for Municipal Sanitation

**Autonomous satellite monitoring and illegal dump detection for smart cities.**

---

## 🚀 PLATFORM OVERVIEW

**Shadow Litter** is a next-generation civic observation platform designed to detect, track, and manage illegal waste dumping using orbital reconnaissance and machine learning. Originally architected for the **Madurai Smart City initiative**, the system leverages high-resolution satellite imagery to provide real-time environmental intelligence.

### 🌓 GLOBAL SYSTEMS
The platform integrates data from multiple constellations:
- **ESA Copernicus (Sentinel-2)**: 10m resolution spectral monitoring (12 bands).
- **ISRO Cartosat-2**: 0.8m panchromatic verification.
- **NASA Prithvi 100M**: Foundation model training weights for waste signature identification.

---

## 🛠️ ARCHITECTURE MAP

```bash
├── apps/
│   ├── web/                # Next.js 15 Premium Control Center (3D Dash)
│   └── api/                # Python/FastAPI Analytical Backend
├── packages/
│   ├── database/           # Prisma-based Multi-Model Schema (JS/Python)
│   ├── shared_types/       # Canonical JSON/Pydantic schemas
│   └── ai_engine/          # ML Training & Inference (PyTorch/Sentinel-2)
├── app/                    # Streamlit Civic Observation Console
├── infra/                  # Kubernetes & Terraform Deployment Templates
└── data/                   # Madurai Zone definitions & GeoJSON maps
```

---

## 🚦 QUICK START

### 1. Requirements
Ensure you have the following installed:
- **Python 3.10+** (with `pip` and `venv`)
- **Node.js 18+** (with `npm` or `pnpm`)
- **Docker & Docker Compose**
- **PostgreSQL** (with PostGIS recommended)

### 2. Environment Setup
Clone the repository and initialize the configuration:
```bash
cp .env.example .env
# Update .env with your credentials
```

### 3. Initialize the Core
Install dependencies and prepare the database:
```bash
# Frontend & Database
cd apps/web && npm install
cd ../../packages/database && npx prisma generate

# Backend AI Engine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Direct Deployment
Run the unified deployment protocol:
```bash
bash deploy.sh
```

---

## 📊 DASHBOARDS

The platform provides two distinct interfaces:
1. **Civic Console (`:8501`)**: Ward-based reporting and temporal analysis for environmental officers.
2. **Premium Command Center (`:3000`)**: High-fidelity 3D visualization and real-time detection metrics for executive monitoring.

---

## 🛰️ REPLICATION & ADAPTATION

To adapt Shadow Litter for a new metropolitan area:
1.  **AOI Correction**: Update `config/city_config.json` with your city's bounding box.
2.  **Basemap Acquisition**: Execute `python scripts/download_basemap.py`.
3.  **Synthesis**: Generate regional synthetic data: `python training/synthesize.py --n_samples 1000`.
4.  **Transfer Learning**: Train the local model: `python training/train.py --epochs 100`.

---

## 📄 LICENSE & GOVERNANCE

**Shadow Litter** is built following the **Premium Software Standards Architecture**.
- **Governance**: Tier 11 High-Fidelity Audit Protocol applied.
- **License**: MIT (See `LICENSE` if present).

---

**Developed for Madurai Smart City | Powered by Orbital Truth.**
