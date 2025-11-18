from __future__ import annotations
import requests
from typing import List, Dict, Any
from src.geo.gazetteer import Gazetteer
from src.geo.resolve import resolve_location

RW_URL = "https://api.reliefweb.int/v1/reports"
TIMEOUT = 20

INCLUDE_FIELDS = [
    "id",
    "title",
    "date.created",
    "primary_country",
    "country",
    "url",
    "disaster",
]

def _normalize(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a ReliefWeb report to unified event schema."""
    fid = item.get("id")
    fields = item.get("fields") or {}
    title = fields.get("title")
    created = (fields.get("date") or {}).get("created")

    lat = lon = None
    country_name = None

    pc = fields.get("primary_country") or {}
    countries = fields.get("country") or []

    # Get country name
    if pc:
        country_name = pc.get("name")
    if not country_name and countries:
        country_name = countries[0].get("name") if isinstance(countries, list) and len(countries) > 0 else None

    # Try to extract coordinates if present (often absent in ReliefWeb)
    for cont in [pc] + (countries if isinstance(countries, list) else []):
        if not cont:
            continue
        for loc in (cont.get("location") or []):
            lat = loc.get("lat")
            lon = loc.get("lon")
            if lat is not None and lon is not None:
                break
        if lat is not None and lon is not None:
            break

    return {
        "id": f"RW-{fid}",
        "source": "ReliefWeb",
        "type": "Report",
        "title": title or "Untitled Report",
        "description": fields.get("body", "")[:500] if fields.get("body") else "",
        "severity": 5.0,
        "lat": lat,
        "lon": lon,
        "country": country_name or "",
        "updated_at": created,  # ISO 8601 string
    }

def fetch_events(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Minimal, reliable GET fetcher for ReliefWeb reports.
    If API is 'warming up' (202), tries once more.
    Always returns a list of normalized rows or [] on failure.
    """
    headers = {
        "Accept": "application/json",
        "User-Agent": "crisis-intel-demo/1.0",
    }
    params = {
        "appname": "crisis-intel-demo",
        "limit": str(limit),
        "profile": "full",
        "sort[]": "date.created:desc",
    }

    try:
        print(f"ReliefWeb: Fetching with GET, limit={limit}")
        r = requests.get(RW_URL, params=params, headers=headers, timeout=TIMEOUT)

        # If 202, try once more
        if r.status_code == 202:
            print("ReliefWeb: Got 202, retrying once...")
            import time
            time.sleep(2)
            r = requests.get(RW_URL, params=params, headers=headers, timeout=TIMEOUT)

        r.raise_for_status()
        data = r.json()
        items = data.get("data") or []

        print(f"ReliefWeb: Received {len(items)} raw items from API")

        # Normalize all items
        normalized = [_normalize(it) for it in items]

        # Resolve locations using gazetteer
        gaz = Gazetteer()
        enriched = [resolve_location(event, gaz) for event in normalized]

        print(f"ReliefWeb: Returning {len(enriched)} enriched events")
        return enriched

    except Exception as e:
        print(f"ReliefWeb: Fetch failed: {e}")
        return []
