from sklearn.linear_model import LogisticRegression
import joblib
import os

def create_baseline_model():
    """Create a lightweight Logistic Regression classifier."""
    return LogisticRegression(C=1.0, max_iter=500, random_state=42)

def save_model(model, path: str):
    """Save trained model to disk."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)

def load_model(path: str):
    """Load trained model from disk."""
    return joblib.load(path)
