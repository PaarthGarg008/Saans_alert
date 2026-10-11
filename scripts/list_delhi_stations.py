"""
list_delhi_stations.py - list OpenAQ monitoring stations around Delhi.

Setup:
  1. Get a free key at https://explore.openaq.org/register
  2. Add to your .env:  OPENAQ_API_KEY=your_key_here
  3. pip install requests python-dotenv
  4. python list_delhi_stations.py

Writes delhi_stations.json and prints a table. Send me the printed table
(or the JSON) so I can build the nearest-station lookup.
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("OPENAQ_API_KEY")
if not KEY:
    sys.exit("OPENAQ_API_KEY not found. Add it to your .env file.")

BASE = "https://api.openaq.org/v3/locations"
HEADERS = {"X-API-Key": KEY}

# Delhi centre. Radius is in metres; the API caps it (about 25 km), so we
# sweep a few centre points to cover Delhi-NCR.
CENTRES = {
    "Central Delhi": (28.6139, 77.2090),
    "North Delhi": (28.7300, 77.1200),
    "East Delhi": (28.6400, 77.3000),
    "South Delhi": (28.5300, 77.2000),
    "West Delhi": (28.6300, 77.0500),
}
RADIUS = 25000


def fetch(lat, lon):
    results, page = [], 1
    while True:
        params = {"coordinates": f"{lat},{lon}", "radius": RADIUS,
                  "limit": 100, "page": page}
        try:
            r = requests.get(BASE, headers=HEADERS, params=params, timeout=20)
        except requests.exceptions.RequestException as e:
            sys.exit(f"Network error: {e}")
        if r.status_code == 401:
            sys.exit("401 Unauthorized: check your API key.")
        if r.status_code == 429:
            sys.exit("429 Rate limited: wait a minute and retry.")
        if r.status_code != 200:
            sys.exit(f"API error {r.status_code}: {r.text[:300]}")
        batch = r.json().get("results", [])
        results.extend(batch)
        if len(batch) < 100:
            return results
        page += 1


def last_seen(loc):
    d = loc.get("datetimeLast")
    if isinstance(d, dict):
        return d.get("utc") or d.get("local") or "?"
    return d or "?"


def main():
    stations = {}
    for name, (lat, lon) in CENTRES.items():
        for loc in fetch(lat, lon):
            stations[loc["id"]] = loc

    rows = []
    for loc in stations.values():
        coords = loc.get("coordinates") or {}
        params = sorted({
            (s.get("parameter") or {}).get("name", "?")
            for s in loc.get("sensors", [])
        })
        provider = (loc.get("provider") or {}).get("name", "?")
        rows.append({
            "id": loc["id"],
            "name": loc.get("name"),
            "lat": coords.get("latitude"),
            "lon": coords.get("longitude"),
            "pollutants": params,
            "provider": provider,
            "last_seen_utc": last_seen(loc),
        })

    rows.sort(key=lambda x: str(x["name"]))
    with open("delhi_stations.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"\nFound {len(rows)} stations. Saved to delhi_stations.json\n")
    print(f"{'ID':<8}{'NAME':<38}{'LAT':<10}{'LON':<10}{'LAST SEEN (UTC)':<22}POLLUTANTS")
    print("-" * 110)
    for x in rows:
        lat = f"{x['lat']:.4f}" if x["lat"] is not None else "?"
        lon = f"{x['lon']:.4f}" if x["lon"] is not None else "?"
        print(f"{x['id']:<8}{str(x['name'])[:36]:<38}{lat:<10}{lon:<10}"
              f"{str(x['last_seen_utc'])[:20]:<22}{','.join(x['pollutants'])}")


if __name__ == "__main__":
    main()
