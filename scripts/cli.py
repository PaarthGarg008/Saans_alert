"""Local mode (no AWS): python scripts/cli.py [area-id|--all] [profile]
Needs OPENWEATHER_API_KEY (+ OPENAQ_API_KEY for station data) in .env or the environment."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from common.advice import PROFILES, get_advice            # noqa: E402
from common.aqi import compute_aqi                         # noqa: E402
from common.areas import get_area, load_areas              # noqa: E402
from common.config import openaq_key, owm_key              # noqa: E402
from common.selector import pick_reading                   # noqa: E402
from common.sources import OpenAQ, owm_current             # noqa: E402


def show(area, aq, key, profile):
    r = pick_reading(area, aq, lambda: owm_current(area["lat"], area["lon"], key))
    a = compute_aqi(r["components"])
    where = {"model": "model estimate",
             "official": f"official: {r['stationName']} ({r['distanceKm']} km)",
             "community": f"community sensor: {r['stationName']} ({r['distanceKm']} km)"}[r["source"]]
    h = r["staleOfficialAgeHours"]
    stale = ("" if not h else "  [no recent official PM2.5 reading - not used]" if h > 168
             else f"  [last official reading was {h} h old - not used]")
    print(f"{area['name']:<26} AQI {a['aqi']:<4}{a['category']:<13}{where}{stale}")
    print(f"   {profile}: {get_advice(profile, a['tier'])}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "--all"
    profile = sys.argv[2] if len(sys.argv) > 2 else "healthy"
    if profile not in PROFILES:
        sys.exit(f"profile must be one of {PROFILES}")
    owm, aq = owm_key(), OpenAQ(openaq_key())
    areas = load_areas() if target == "--all" else [get_area(target)]
    if None in areas:
        sys.exit("unknown area id; see backend/common/areas.json")
    for a in areas:
        show(a, aq, owm, profile)