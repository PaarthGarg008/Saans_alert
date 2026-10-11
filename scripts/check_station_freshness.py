"""
check_station_freshness.py - for a shortlist of OpenAQ stations, fetch the
LATEST PM2.5 / PM10 readings, show how old they are, and the estimated AQI.

Put it in the same folder as air_engine.py and your .env (needs OPENAQ_API_KEY).
Run:  python check_station_freshness.py
Then send me the printed table.
"""
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from air_engine import cpcb_aqi  # reuse the AQI calculation

load_dotenv()
KEY = os.getenv("OPENAQ_API_KEY")
if not KEY:
    sys.exit("OPENAQ_API_KEY not found in .env")

HEADERS = {"X-API-Key": KEY}
BASE = "https://api.openaq.org/v3/locations"

# id: label.  Government stations (most recent entries) + a few fresh
# low-cost / other sensors for comparison.
STATIONS = {
    235: "Anand Vihar (DPCC)",
    10831: "Rohini (DPCC)",
    17: "R K Puram (DPCC)",
    6931: "Dwarka Sector 8 (DPCC)",
    5613: "ITO (CPCB)",
    8239: "Okhla Phase-2 (DPCC)",
    50: "Punjabi Bagh (DPCC)",
    10485: "Narela (DPCC)",
    8472: "Bawana (DPCC)",
    8915: "Wazirpur (DPCC)",
    8118: "New Delhi (pm25 only)",
    4663956: "Santushti Apts, Vasant Kunj (sensor)",
    6145551: "Anand Lok (sensor)",
    2860223: "GK1 Oberoi Terrace (sensor)",
    4712609: "Air Check (sensor)",
}


def get(url):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
        except requests.exceptions.RequestException as e:
            print(f"  network error: {e}")
            return None
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code != 200:
            print(f"  API {r.status_code}: {r.text[:150]}")
            return None
        return r.json()
    return None


def parse_utc(dt):
    s = dt.get("utc") if isinstance(dt, dict) else dt
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def check(loc_id, label):
    meta = get(f"{BASE}/{loc_id}")
    time.sleep(1)
    latest = get(f"{BASE}/{loc_id}/latest")
    time.sleep(1)
    if not meta or not latest or not meta.get("results"):
        return {"id": loc_id, "label": label, "error": "no data"}

    # sensor id -> parameter name
    sensors = {}
    for s in meta["results"][0].get("sensors", []):
        p = s.get("parameter") or {}
        sensors[s["id"]] = p.get("name")

    vals, newest = {}, None
    for item in latest.get("results", []):
        name = sensors.get(item.get("sensorsId"))
        when = parse_utc(item.get("datetime"))
        if name in ("pm25", "pm10") and item.get("value") is not None:
            vals[name] = (item["value"], when)
        if when and (newest is None or when > newest):
            newest = when

    now = datetime.now(timezone.utc)
    age = (now - newest).total_seconds() / 3600 if newest else None

    aqi = None
    comp = {}
    if "pm25" in vals:
        comp["pm2_5"] = vals["pm25"][0]
    if "pm10" in vals:
        comp["pm10"] = vals["pm10"][0]
    if comp:
        aqi = cpcb_aqi(comp)
    return {"id": loc_id, "label": label, "pm25": vals.get("pm25", (None,))[0],
            "pm10": vals.get("pm10", (None,))[0], "age_h": age, "aqi": aqi}


def main():
    print(f"\nNow (UTC): {datetime.now(timezone.utc):%Y-%m-%d %H:%M}\n")
    print(f"{'ID':<9}{'STATION':<38}{'PM2.5':<9}{'PM10':<9}{'AGE (hours)':<13}ESTIMATED AQI")
    print("-" * 100)
    for loc_id, label in STATIONS.items():
        r = check(loc_id, label)
        if "error" in r:
            print(f"{loc_id:<9}{label:<38}{r['error']}")
            continue
        age = f"{r['age_h']:.1f}" if r["age_h"] is not None else "?"
        aqi = f"{r['aqi'][0]} ({r['aqi'][1]})" if r["aqi"] else "-"
        pm25 = round(r["pm25"], 1) if r["pm25"] is not None else "-"
        pm10 = round(r["pm10"], 1) if r["pm10"] is not None else "-"
        print(f"{loc_id:<9}{label:<38}{str(pm25):<9}{str(pm10):<9}{age:<13}{aqi}")


if __name__ == "__main__":
    main()
