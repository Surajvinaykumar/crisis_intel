import os
import requests
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.geo.gazetteer import Gazetteer
from src.geo.resolve import resolve_location

class TwitterFetcher:
    """Fetches crisis-related tweets using Twitter API v2 with Bearer token auth."""

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.bearer_token = None

    def _get_bearer_token(self) -> Optional[str]:
        """Obtain Bearer token using client credentials flow."""
        try:
            credentials = f"{self.api_key}:{self.api_secret}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {b64_credentials}",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
            }

            data = {"grant_type": "client_credentials"}

            response = requests.post(
                "https://api.twitter.com/oauth2/token",
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()

            token_data = response.json()
            return token_data.get("access_token")

        except Exception as e:
            print(f"Error obtaining Twitter Bearer token: {e}")
            return None

    def fetch_events(self) -> List[Dict[str, Any]]:
        """Fetch recent crisis-related tweets."""
        if not self.bearer_token:
            self.bearer_token = self._get_bearer_token()
            if not self.bearer_token:
                print("Failed to obtain Twitter Bearer token")
                return []

        try:
            headers = {"Authorization": f"Bearer {self.bearer_token}"}

            query = "(earthquake OR flood OR wildfire OR cyclone OR hurricane OR landslide) -is:retweet lang:en"

            params = {
                "query": query,
                "max_results": 50,
                "tweet.fields": "created_at,geo,text,lang",
                "expansions": "geo.place_id",
                "place.fields": "full_name,id,geo"
            }

            response = requests.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()

            data = response.json()
            tweets = data.get("data", [])
            places = {p["id"]: p for p in data.get("includes", {}).get("places", [])}

            gaz = Gazetteer()
            events = []

            for tweet in tweets:
                lat, lon = None, None
                bbox = None
                place_name = None
                country_code = None

                if "geo" in tweet and "place_id" in tweet["geo"]:
                    place_id = tweet["geo"]["place_id"]
                    place = places.get(place_id)

                    if place:
                        place_name = place.get("full_name", "")
                        country_code = place.get("country_code", "")

                        if "geo" in place and "bbox" in place["geo"]:
                            bbox = place["geo"]["bbox"]
                            lon = (bbox[0] + bbox[2]) / 2
                            lat = (bbox[1] + bbox[3]) / 2

                event = {
                    "id": f"TW-{tweet['id']}",
                    "source": "Twitter",
                    "type": "Report",
                    "title": tweet["text"][:100],
                    "description": tweet["text"],
                    "severity": 5.0,
                    "lat": lat,
                    "lon": lon,
                    "bbox": bbox,
                    "place_name": place_name or "",
                    "country_code": country_code or "",
                    "updated_at": tweet.get("created_at", datetime.utcnow().isoformat() + "Z")
                }

                event = resolve_location(event, gaz)
                events.append(event)

            return events

        except Exception as e:
            print(f"Error fetching Twitter events: {e}")
            return []
