import os
import csv
import unicodedata
import re
from typing import Optional, Dict, Tuple

class Gazetteer:
    """Local gazetteer for fast location lookups using CSV data."""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            data_dir = os.path.join(base_dir, "data", "geo")

        self.country_by_iso2 = {}
        self.country_by_iso3 = {}
        self.country_by_name = {}
        self.admin1_by_key = {}
        self.cities_by_key = {}

        self._load_countries(os.path.join(data_dir, "country_centroids.csv"))
        self._load_admin1(os.path.join(data_dir, "admin1_centroids.csv"))
        self._load_cities(os.path.join(data_dir, "cities_light.csv"))

        self._build_aliases()

    def _normalize(self, text: str) -> str:
        """Normalize text for matching: lowercase, remove accents, strip."""
        if not text:
            return ""
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        text = text.lower().strip()
        text = re.sub(r'[^\w\s\-,]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    def _load_countries(self, path: str):
        """Load country centroids from CSV."""
        if not os.path.exists(path):
            print(f"Warning: Country centroids file not found: {path}")
            return

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                iso2 = row['iso2'].upper()
                iso3 = row['iso3'].upper()
                name = row['name']
                lat = float(row['lat'])
                lon = float(row['lon'])
                pop = int(row.get('population', 0))

                entry = {'lat': lat, 'lon': lon, 'name': name, 'iso2': iso2, 'iso3': iso3, 'pop': pop}

                self.country_by_iso2[iso2] = entry
                self.country_by_iso3[iso3] = entry
                self.country_by_name[self._normalize(name)] = entry

    def _load_admin1(self, path: str):
        """Load admin1 (state/province) centroids from CSV."""
        if not os.path.exists(path):
            print(f"Warning: Admin1 centroids file not found: {path}")
            return

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                country_iso2 = row['country_iso2'].upper()
                admin1_name = row['admin1_name']
                lat = float(row['lat'])
                lon = float(row['lon'])

                key = f"{country_iso2}:{self._normalize(admin1_name)}"
                self.admin1_by_key[key] = {
                    'lat': lat,
                    'lon': lon,
                    'name': admin1_name,
                    'country_iso2': country_iso2
                }

    def _load_cities(self, path: str):
        """Load city centroids from CSV."""
        if not os.path.exists(path):
            print(f"Warning: Cities file not found: {path}")
            return

        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                country_iso2 = row['country_iso2'].upper()
                admin1_name = row['admin1_name']
                city = row['city']
                lat = float(row['lat'])
                lon = float(row['lon'])
                pop = int(row.get('pop', 0))

                norm_city = self._normalize(city)
                norm_admin1 = self._normalize(admin1_name)

                key = f"{country_iso2}:{norm_admin1}:{norm_city}"
                key_country = f"{country_iso2}:{norm_city}"

                entry = {
                    'lat': lat,
                    'lon': lon,
                    'name': city,
                    'admin1_name': admin1_name,
                    'country_iso2': country_iso2,
                    'pop': pop
                }

                self.cities_by_key[key] = entry

                if key_country not in self.cities_by_key or pop > self.cities_by_key[key_country].get('pop', 0):
                    self.cities_by_key[key_country] = entry

    def _build_aliases(self):
        """Build common country name aliases."""
        aliases = {
            'usa': 'US',
            'u.s.': 'US',
            'united states of america': 'US',
            'america': 'US',
            'uk': 'GB',
            'united kingdom': 'GB',
            'britain': 'GB',
            'england': 'GB',
            'drc': 'CD',
            'democratic republic of the congo': 'CD',
            'uae': 'AE',
            'emirates': 'AE',
        }

        for alias, iso2 in aliases.items():
            norm_alias = self._normalize(alias)
            if iso2 in self.country_by_iso2 and norm_alias not in self.country_by_name:
                self.country_by_name[norm_alias] = self.country_by_iso2[iso2]

    def find_country(self, name_or_code: str) -> Optional[Dict]:
        """Find country by ISO code or name."""
        if not name_or_code:
            return None

        code_upper = name_or_code.upper().strip()

        if len(code_upper) == 2 and code_upper in self.country_by_iso2:
            return self.country_by_iso2[code_upper]

        if len(code_upper) == 3 and code_upper in self.country_by_iso3:
            return self.country_by_iso3[code_upper]

        norm_name = self._normalize(name_or_code)
        return self.country_by_name.get(norm_name)

    def find_admin1(self, country_code: str, admin1_name: str) -> Optional[Dict]:
        """Find admin1 (state/province) by country and name."""
        if not country_code or not admin1_name:
            return None

        country_code_upper = country_code.upper().strip()
        norm_admin1 = self._normalize(admin1_name)

        key = f"{country_code_upper}:{norm_admin1}"
        return self.admin1_by_key.get(key)

    def find_city(self, country_code: str, admin1_name: Optional[str], city_name: str) -> Optional[Dict]:
        """Find city by country, optional admin1, and city name."""
        if not country_code or not city_name:
            return None

        country_code_upper = country_code.upper().strip()
        norm_city = self._normalize(city_name)

        if admin1_name:
            norm_admin1 = self._normalize(admin1_name)
            key = f"{country_code_upper}:{norm_admin1}:{norm_city}"
            if key in self.cities_by_key:
                return self.cities_by_key[key]

        key_country = f"{country_code_upper}:{norm_city}"
        return self.cities_by_key.get(key_country)
