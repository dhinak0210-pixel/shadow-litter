# SHADOW LITTER: Manual Annotation Guide (Step 1.1)

This guide outlines the process for creating high-fidelity ground truth labels using the `RealAnnotationTool`.

## 1. Prerequisites 📋
- **Standard Image**: A 4-band GeoTIFF (RGB + NIR) downloaded via `scripts/acquire_data.py`.
- **Environment**: Desktop environment with X11 support (needed for OpenCV GUI).
- **Resolution**: Sentinel-2 (10m) resolution implies that a 100sqm dump is approximately 1 pixel. We focus on clusters.

## 2. Launching the Tool 🚀
Run the script pointing to your downloaded imagery:
```bash
source venv/bin/activate
python -m src.annotation.real_labeling_system --image path/to/madurai_2024_02.tif
```

## 3. Interaction Controls 🖱️
- **Left Click**: Add a vertex to the current polygon.
- **Right Click**: Undo the last vertex.
- **'s' Key**: Save the current polygon and associate it with a dump type.
- **'c' Key**: Clear current (unsaved) polygon.
- **'n' Key**: Cycle through dump categories (Fresh, Construction, Leachate).
- **'q' Key**: Quit and export results.

## 4. Labeling Strategy 🔍
1. **Identify High Contrast Areas**: Look for white/grey irregular patches in barren land or near informal settlements.
2. **NIR Cross-Check**: The tool automatically uses the Near-Infrared band to help distinguish between vegetation (bright in NIR) and inorganic waste.
3. **Temporal Verification**: Open Google Earth Pro alongside to verify the site history if unsure.

## 5. Output 📁
- The tool saves a `labels.json` in COCO format.
- Corresponding GeoJSON files are generated for GIS integration.
- Target: **500 verified polygons** for the v1.0 training set.
