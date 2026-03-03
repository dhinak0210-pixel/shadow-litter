# SHADOW LITTER: Web Search & Weak Supervision Pipeline (Step 1.2)

This guide details how to leverage OpenStreetMap (OSM) and news sources to bootstrap dump labels.

## 1. Automated OSM Querying 🗺️
The `RealWeakSupervisor` class uses the Overpass API to find:
- `landuse=construction`: High correlation with construction debris.
- `abandoned=yes`: Potential unofficial dump sites.
- `informal=yes`: High-risk zones for municipal solid waste.

Run the query:
```bash
python -m src.annotation.weak_supervision_real --mode osm
```

## 2. Scraping Real Intelligence 📰
The system targets local news reports (The Hindu, Times of India - Madurai Edition) using keywords:
- "dump yard", "garbage pile", "burning waste", "sanitation complaint".
- Extracted locations are geocoded using Nominatim.

## 3. Merging Signals 🔗
- Geocoded news reports are cross-referenced with Sentinel-2 imagery dates.
- High-confidence news reports are converted into bounding boxes for manual verification.

## 4. Integration with Manual Pipeline 🛰️
1. Download Sentinel-2 tile for the reported coordinates.
2. Load the tile in `RealAnnotationTool`.
3. Verify if visual evidence of waste exists.
4. Save as "Verified" ground truth.
