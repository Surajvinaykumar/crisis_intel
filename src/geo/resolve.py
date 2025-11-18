from typing import Dict, Optional, Tuple
from src.geo.gazetteer import Gazetteer

def bbox_centroid(bbox: list) -> Optional[Tuple[float, float]]:
    """Calculate centroid of bounding box [minLon, minLat, maxLon, maxLat]."""
    if not bbox or len(bbox) != 4:
        return None

    try:
        min_lon, min_lat, max_lon, max_lat = [float(x) for x in bbox]
        lat = (min_lat + max_lat) / 2
        lon = (min_lon + max_lon) / 2

        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return (lat, lon)
    except (ValueError, TypeError):
        pass

    return None

def resolve_location(rec: dict, gaz: Gazetteer, online: Optional[object] = None) -> dict:
    """
    Resolve location for an event record using multiple strategies.

    Returns enriched record with:
    - lat, lon: coordinates
    - loc_method: how the location was determined
    - loc_confidence: confidence score 0-1
    - loc_notes: brief description
    """
    result = rec.copy()

    result['loc_method'] = None
    result['loc_confidence'] = 0.0
    result['loc_notes'] = ''

    lat = result.get('lat')
    lon = result.get('lon')

    if lat is not None and lon is not None:
        try:
            lat = float(lat)
            lon = float(lon)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                result['lat'] = lat
                result['lon'] = lon
                result['loc_method'] = 'provided_point'
                result['loc_confidence'] = 1.0
                result['loc_notes'] = 'Coordinates provided in source data'
                return result
        except (ValueError, TypeError):
            pass

    bbox = result.get('bbox')
    if bbox:
        centroid = bbox_centroid(bbox)
        if centroid:
            result['lat'], result['lon'] = centroid
            result['loc_method'] = 'bbox_centroid'
            result['loc_confidence'] = 0.8
            result['loc_notes'] = 'Centroid of bounding box'
            return result

    country_code = result.get('country_code', '').strip().upper()
    country_name = result.get('country', '').strip()
    admin1_name = result.get('admin1', '').strip()
    city_name = result.get('city', '').strip()
    place_name = result.get('place_name', '').strip()

    country_data = None
    if country_code:
        country_data = gaz.find_country(country_code)
    if not country_data and country_name:
        country_data = gaz.find_country(country_name)

    if city_name and country_data:
        city_data = gaz.find_city(country_data['iso2'], admin1_name, city_name)
        if city_data:
            result['lat'] = city_data['lat']
            result['lon'] = city_data['lon']
            result['loc_method'] = 'city_geocode'
            confidence = 0.75
            if admin1_name:
                confidence += 0.05
            if city_data.get('pop', 0) > 1000000:
                confidence += 0.05
            result['loc_confidence'] = min(confidence, 1.0)
            result['loc_notes'] = f"City: {city_data['name']}, {country_data['name']}"
            return result

    if place_name and country_data:
        if ',' in place_name:
            parts = [p.strip() for p in place_name.split(',')]
            if len(parts) >= 2:
                possible_city = parts[0]
                possible_admin1 = parts[1] if len(parts) > 1 else None

                city_data = gaz.find_city(country_data['iso2'], possible_admin1, possible_city)
                if city_data:
                    result['lat'] = city_data['lat']
                    result['lon'] = city_data['lon']
                    result['loc_method'] = 'city_geocode'
                    result['loc_confidence'] = 0.72
                    result['loc_notes'] = f"Parsed from place name: {city_data['name']}"
                    return result

    if admin1_name and country_data:
        admin1_data = gaz.find_admin1(country_data['iso2'], admin1_name)
        if admin1_data:
            result['lat'] = admin1_data['lat']
            result['lon'] = admin1_data['lon']
            result['loc_method'] = 'admin1_centroid'
            result['loc_confidence'] = 0.7
            result['loc_notes'] = f"Admin1: {admin1_data['name']}, {country_data['name']}"
            return result

    if country_data:
        result['lat'] = country_data['lat']
        result['lon'] = country_data['lon']
        result['loc_method'] = 'country_centroid'
        result['loc_confidence'] = 0.6
        result['loc_notes'] = f"Country: {country_data['name']}"
        return result

    result['loc_notes'] = 'Could not resolve location'
    return result

def enrich_events(events: list, gaz: Optional[Gazetteer] = None) -> list:
    """Enrich a list of events with resolved locations."""
    if gaz is None:
        gaz = Gazetteer()

    enriched = []
    for event in events:
        enriched_event = resolve_location(event, gaz)
        enriched.append(enriched_event)

    return enriched
