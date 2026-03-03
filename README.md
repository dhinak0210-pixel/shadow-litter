# Shadow Litter Replication Guide

## Quick Start (Any City)
1. Update `config/city_config.json` with bounding box
2. Run `python scripts/download_basemap.py`
3. Generate synthetic training data: `python training/synthesize.py --n_samples 1000`
4. Train: `python training/train.py --epochs 100`
5. Deploy: `docker-compose up`

## City Adaptation Checklist
- [ ] Define AOI bounding box
- [ ] Obtain ward boundaries (GeoJSON)
- [ ] Collect 10 validation samples
- [ ] Adjust spectral indices for local climate
- [ ] Calibrate detection thresholds
