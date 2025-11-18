import requests
from typing import List, Dict, Any

def fetch_events() -> List[Dict[str, Any]]:
    """Fetch recent natural events from NASA EONET API v3."""
    try:
        response = requests.get(
            "https://eonet.gsfc.nasa.gov/api/v3/events",
            timeout=15
        )
        response.raise_for_status()

        data = response.json()
        raw_events = data.get("events", [])

        events = []
        for evt in raw_events:
            geometries = evt.get("geometry", [])
            if not geometries:
                continue

            latest_geo = geometries[-1]
            coords = latest_geo.get("coordinates")

            if not coords or len(coords) < 2:
                continue

            lon, lat = coords[0], coords[1]

            categories = evt.get("categories", [])
            cat_title = categories[0].get("title", "") if categories else ""

            severity = 7.0 if cat_title in ["Wildfires", "Severe Storms"] else 5.0

            event = {
                "id": f"EONET-{evt['id']}",
                "source": "EONET",
                "type": cat_title or "Natural Event",
                "title": evt.get("title", "Untitled Event"),
                "description": evt.get("description", ""),
                "severity": severity,
                "lat": lat,
                "lon": lon,
                "updated_at": latest_geo.get("date", evt.get("geometry", [{}])[0].get("date", ""))
            }
            events.append(event)

        return events

    except Exception as e:
        print(f"Error fetching EONET events: {e}")
        return []
