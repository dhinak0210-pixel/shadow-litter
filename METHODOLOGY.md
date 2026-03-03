# METHODOLOGY.md — shadow-litter

## Academic Methods Section

### 1. Study Area

Madurai district, Tamil Nadu, India (9.9252°N, 78.1198°E) covers ~3,741 km² with a
population of ~3.1 million. Five high-risk waste monitoring zones were identified based on
historical dumping records, water body proximity, and urban growth patterns.

### 2. Satellite Data Acquisition

**Sentinel-2 MSI (Level-2A):** Six spectral bands were selected covering
visible (B02-B04), near-infrared (B08), and short-wave infrared (B11, B12) at
10–20m spatial resolution. Images with ≤20% cloud cover were downloaded from
ESA Copernicus Open Access Hub.

**Landsat 8/9 TIRS (Collection 2 Level-2):** Band 10 thermal infrared (10.9μm)
was used to extract brightness temperature anomalies (T > 305K) consistent with
decomposition heat signatures at active dump sites.

### 3. Preprocessing Pipeline

1. **Atmospheric correction:** Level-2A products are pre-corrected with Sen2Cor.
2. **Cloud masking:** Scene Classification Layer (SCL Band) used to mask cloud/shadow.
3. **Coregistration:** Phase correlation on NIR band for sub-pixel alignment (OpenCV).
4. **Histogram matching:** CDF-based cross-date harmonization to remove illumination bias.
5. **Patch extraction:** 256×256 overlapping tiles (stride=128) yielding 800–2000 patches/image.

### 4. Change Detection Model

**Architecture:** Siamese U-Net with ResNet-50 encoder (ImageNet pretrained). 
Two temporal branches share encoder weights. A difference module computes 
L1 absolute differences with channel-wise Squeeze-and-Excitation (SE) attention 
at each encoder scale. This highlights spectral anomalies while suppressing 
common temporal noise like seasonal vegetation cycles.

**Training & Fine-Tuning:**
- **Phase 1 (Self-Supervised):** Temporal contrastive pretraining on 10,000 unlabeled pairs.
- **Phase 2 (Synthetic Supervised):** Fine-tuning on 500 high-fidelity synthetic samples.
- **Benchmark Performance:** Target F1 score of >0.85 on the synthetic validation set.

### 5. Synthetic Data Generation

Three waste archetypes synthesized via spectral manipulation:
- **Construction debris:** Angular dark patches, elevated SWIR reflectance.
- **Household waste:** Gaussian blob morphology, NIR suppression.
- **Leachate pools:** All-band darkening, water-like spectral signature.

Poisson-based blending applied for photorealistic integration.

### 6. Post-Processing

1. Threshold change probability map at τ=0.75.
2. Connected component analysis → individual dump polygons.
3. Filter by minimum area A_min=500 m².
4. Spectral classification (Random Forest, 18 features) → dump type.
5. Temporal verification against 2-year pixel history.

### 7. Validation

- **Synthetic benchmark:** 50 controlled patches, target >80% recall, <20% FPR.
- **Cross-reference validation:** NLP extraction from local news corpora (The Hindu Madurai).
- **Ground truth:** Crowd-sourced verification via Shadow Litter Explorer app.

### 8. Operational Deployment

Fully automated weekly scan pipeline deployed on Hugging Face Spaces (free tier).
Alert distribution via Twilio WhatsApp API and weekly PDF reports to Madurai Corporation.
