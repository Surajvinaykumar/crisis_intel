import pandas as pd
from typing import List, Dict, Any

HIGH_RISK_TYPES = [
    "Wildfires", "Severe Storms", "Earthquakes", "Floods",
    "Volcanoes", "Cyclones", "Hurricanes", "Tsunami"
]

def extract_features(events: List[Dict[str, Any]]) -> pd.DataFrame:
    """Extract ML features from events."""
    df = pd.DataFrame(events)

    if df.empty:
        return pd.DataFrame(columns=["sev", "has_coords", "is_high_type", "src_eonet", "src_relief"])

    df["sev"] = df["severity"].fillna(5.0)
    df["has_coords"] = ((df["lat"].notna()) & (df["lon"].notna())).astype(int)

    df["is_high_type"] = df["type"].apply(
        lambda t: 1 if t in HIGH_RISK_TYPES else 0
    ).astype(int)

    df["src_eonet"] = (df["source"] == "EONET").astype(int)
    df["src_relief"] = (df["source"] == "ReliefWeb").astype(int)

    feature_cols = ["sev", "has_coords", "is_high_type", "src_eonet", "src_relief"]

    return df[feature_cols]

def make_labels(events: List[Dict[str, Any]]) -> List[int]:
    """Create heuristic labels for training: 1 = major crisis risk, 0 = minor."""
    df = pd.DataFrame(events)

    if df.empty:
        return []

    df["sev"] = df["severity"].fillna(5.0)
    df["has_coords"] = ((df["lat"].notna()) & (df["lon"].notna())).astype(int)
    df["is_high_type"] = df["type"].apply(
        lambda t: 1 if t in HIGH_RISK_TYPES else 0
    ).astype(int)

    labels = []
    for idx, row in df.iterrows():
        if row["sev"] >= 6.5:
            labels.append(1)
        elif row["is_high_type"] == 1 and row["has_coords"] == 1:
            labels.append(1)
        else:
            labels.append(0)

    return labels
