from src.db import read_events
from src.features import extract_features, make_labels
from src.models.baseline_classifier import create_baseline_model, save_model
import os

def train_model(save_path: str = "artifacts/baseline_crisis_lr.joblib"):
    """Train baseline Logistic Regression model on crisis events."""
    events = read_events()

    if len(events) < 10:
        raise ValueError(f"Need at least 10 events to train; found {len(events)}")

    X = extract_features(events)
    y = make_labels(events)

    if X.empty:
        raise ValueError("Feature extraction returned empty DataFrame")

    model = create_baseline_model()
    model.fit(X, y)

    save_model(model, save_path)

    class_counts = {0: y.count(0), 1: y.count(1)}

    return {
        "model_path": save_path,
        "n_samples": len(events),
        "class_distribution": class_counts,
        "features": list(X.columns)
    }
