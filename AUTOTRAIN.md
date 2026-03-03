# Shadow Litter: Auto-Training & Self-Improvement 🤖🛰️
"The model teaches itself. The data generates itself. The intelligence grows without human intervention."

---

## 🏗️ Architecture Overview

The system is designed as a **Continuous Intelligence Loop**. It doesn't rely on static datasets; instead, it uses the 10-meter resolution archive of the planet as its classroom.

### 1. Self-Supervised Foundation (Phase 0)
- **SimSat (Temporal Contrastive)**: Uses `src/auto_training/temporal_contrastive.py` to learn representations by comparing temporal pairs. It asks: *"Is this the same place at a different time?"*
- **SatMAE (Masked Autoencoder)**: Uses `src/auto_training/satmae_pretrain.py` to reconstruct missing patches of the planet, learning deep spatial-spectral patterns.

### 2. Weak Supervision Bootstrap (Phase 1)
- **OSM Signal Detection**: `src/auto_training/weak_supervision_signals.py` extracts construction sites from OpenStreetMap as noisy but abundant training signals.
- **Temporal Teacher**: `src/auto_training/temporal_teacher.py` analyzes the multi-year archive to find stable vs. suddenly-persistent changes, creating pseudo-labels automatically.

### 3. Active Learning & Gamification (Phase 2)
- **Uncertainty Oracle**: `src/auto_training/active_learning_oracle.py` identifies regions where the model is "confused" (high entropy) and prioritizes them for labeling.
- **Arena (Gamified Labeling)**: `src/auto_training/gamified_labeling.py` provides the logic for a platform where users earn points for verifying detections.

### 4. Synthetic Data Arms Race (Phase 3)
- **Procedural Dumps**: `src/auto_training/procedural_dumps.py` generates unlimited variations of waste signatures (RGB+NIR).
- **GAN Refinement**: `src/auto_training/gan_refinement.py` refines these procedural dumps to be indistinguishable from real satellite imagery.

### 5. Continuous MLOps (Phase 4)
- **Orchestrator**: `src/auto_training/continuous_learning.py` monitors the system and automatically triggers retraining, validation, and canary deployments.

---

## 🚀 Operations

### To initiate the Autonomous Intelligence Loop:
```bash
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.
python src/auto_training/continuous_learning.py
```

### Key Metrics
- **Representation Quality**: Measured via linear probing on self-supervised features.
- **Labeling Efficiency**: Informative value per human-second (Active Learning).
- **Synthetic Fidelity**: GAN discriminator score vs. Real imagery.

---
*Autonomous orbital intelligence for the common good. Built for Madurai.*
