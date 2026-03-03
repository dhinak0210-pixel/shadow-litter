"""
src/models/spectral_classifier.py
───────────────────────────────────
DumpTypeClassifier — classifies detected change regions by dump type.
Input: changed region spectral signature + texture features.
Output: class label + confidence.

Classes:
  0 = false_positive  (water reflection, cloud shadow, seasonal veg change)
  1 = fresh_dump      (new household/organic waste accumulation)
  2 = construction_debris  (concrete,砂, gravel, building materials)
  3 = leachate        (chemical seepage, dark water contamination)
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score

logger = logging.getLogger(__name__)

CLASSES = ["false_positive", "fresh_dump", "construction_debris", "leachate"]
N_CLASSES = len(CLASSES)

# Band indices in standard 6-band stack
B_BLUE, B_GREEN, B_RED, B_NIR, B_SWIR1, B_SWIR2 = 0, 1, 2, 3, 4, 5


def extract_spectral_features(patch: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Extract a spectral feature vector from a (C, H, W) satellite patch.
    If mask is provided, only considers pixels within the detected region.

    Features:
        Band statistics (mean, std) × 6 bands        = 12
        Spectral indices (NDVI, NDWI, NDBI, SWIR)    = 4
        Texture (GLCM contrast approximation)        = 2
        Total                                        = 18
    """
    if mask is not None and mask.sum() > 0:
        # Extract only pixels inside the detection mask
        region = patch[:, mask > 0]  # (C, N_pixels)
    else:
        region = patch.reshape(patch.shape[0], -1)  # (C, H*W)

    b = region   # (C, N)
    eps = 1e-8

    # Band statistics
    band_means = b.mean(axis=1)   # (C,)
    band_stds  = b.std(axis=1)    # (C,)

    # Spectral indices
    ndvi  = (b[B_NIR] - b[B_RED]) / (b[B_NIR] + b[B_RED] + eps)
    ndwi  = (b[B_GREEN] - b[B_NIR]) / (b[B_GREEN] + b[B_NIR] + eps)
    ndbi  = (b[B_SWIR1] - b[B_NIR]) / (b[B_SWIR1] + b[B_NIR] + eps)
    swir_ratio = b[B_SWIR2] / (b[B_SWIR1] + eps)

    indices = np.array([
        ndvi.mean(), ndwi.mean(), ndbi.mean(), swir_ratio.mean()
    ])

    # Simple texture proxy: local std within window
    nir_patch = patch[B_NIR]
    texture_contrast = float(nir_patch.std())
    texture_entropy  = float(-np.sum(np.abs(np.diff(nir_patch.ravel()[:100]))))

    features = np.concatenate([band_means, band_stds, indices, [texture_contrast, texture_entropy]])
    return features.astype(np.float32)


class DumpTypeClassifier:
    """Random Forest dump type classifier with spectral feature extraction."""

    def __init__(self, n_estimators: int = 200, max_depth: int = 10, seed: int = 42):
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=max_depth,
                random_state=seed,
                n_jobs=-1,
                class_weight="balanced",
            )),
        ])
        self.is_fitted = False

    def fit(
        self,
        patches: list[np.ndarray],
        labels: list[int],
        masks: Optional[list[np.ndarray]] = None,
    ) -> "DumpTypeClassifier":
        """
        Train on labeled examples.

        Args:
            patches: List of (C, H, W) satellite patches
            labels:  Integer class labels (0-3)
            masks:   Optional binary masks of detected regions
        """
        X = np.stack([
            extract_spectral_features(p, masks[i] if masks else None)
            for i, p in enumerate(patches)
        ])
        y = np.array(labels)

        # Cross-validation score
        cv_scores = cross_val_score(self.pipeline, X, y, cv=5, scoring="f1_weighted")
        logger.info(f"CV F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

        self.pipeline.fit(X, y)
        self.is_fitted = True
        logger.info(f"✅ DumpTypeClassifier fitted on {len(patches)} samples")
        return self

    def predict(
        self,
        patch: np.ndarray,
        mask: Optional[np.ndarray] = None,
    ) -> tuple[str, float]:
        """
        Classify a single detection.

        Returns:
            (class_name, confidence_score)
        """
        if not self.is_fitted:
            raise RuntimeError("Classifier not fitted. Call .fit() or .load() first.")
        features = extract_spectral_features(patch, mask).reshape(1, -1)
        probs = self.pipeline.predict_proba(features)[0]
        class_idx = int(np.argmax(probs))
        return CLASSES[class_idx], float(probs[class_idx])

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self.pipeline, f)
        logger.info(f"Classifier saved → {path}")

    def load(self, path: str) -> "DumpTypeClassifier":
        with open(path, "rb") as f:
            self.pipeline = pickle.load(f)
        self.is_fitted = True
        logger.info(f"Classifier loaded from {path}")
        return self


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Smoke test with synthetic data
    import numpy as np
    rng = np.random.default_rng(42)
    patches = [rng.random((6, 64, 64), dtype=np.float32) for _ in range(100)]
    labels = rng.integers(0, N_CLASSES, size=100).tolist()
    clf = DumpTypeClassifier()
    clf.fit(patches, labels)
    cls_name, conf = clf.predict(patches[0])
    print(f"Prediction: {cls_name}  ({conf:.1%} confidence)")
