from typing import List, Dict, Any
import joblib
import os
from src.features import extract_features

def score_events(events: List[Dict[str, Any]], model_path: str) -> List[Dict[str, Any]]:
    """Score events using a trained model and add ml_risk field."""
    if not os.path.exists(model_path):
        print(f"Model not found at {model_path}")
        return events

    try:
        model = joblib.load(model_path)
    except Exception as e:
        print(f"Error loading model: {e}")
        return events

    if not events:
        return events

    X = extract_features(events)

    if X.empty:
        return events

    try:
        predictions = model.predict(X)
        probabilities = model.predict_proba(X)

        for i, event in enumerate(events):
            event["ml_risk"] = int(predictions[i])
            event["priority_score"] = float(probabilities[i][1])

    except Exception as e:
        print(f"Error scoring events: {e}")

    return events
