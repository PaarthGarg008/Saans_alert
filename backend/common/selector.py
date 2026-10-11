"""Tiered source selection (guide section 10.7). A stale reading NEVER drives advice.

 1. official station : age <= 3 h, PM2.5 present, nearest within 8 km
 2. community sensor : age <= 2 h, PM2.5 present, nearest within 5 km
 3. OpenWeatherMap model estimate (always available)
"""
import logging
import math
from datetime import datetime, timezone

from .sources import SourceError

log = logging.getLogger(__name__)

TIERS = (("official", "officialStationIds", 3.0, 8.0),
         ("community", "sensorIds", 2.0, 5.0))


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def _fresh_reading(st, now, max_age_h):
    """-> (reading or None, age_hours or None)."""
    pm25 = st.get("pm25")
    if not pm25:
        return None, None
    age = (now - pm25[1]).total_seconds() / 3600
    if age > max_age_h or age < -0.25:          # too old, or timestamp from the future
        return None, age
    comps = {"pm2_5": round(pm25[0], 1)}
    pm10 = st.get("pm10")
    if pm10 and 0 <= (now - pm10[1]).total_seconds() / 3600 <= max_age_h:
        comps["pm10"] = round(pm10[0], 1)
    return {"components": comps, "ts": int(pm25[1].timestamp())}, age


def pick_reading(area, openaq, model_fn, now=None):
    """model_fn() -> (components, epoch_ts). Returns a dict describing the chosen reading."""
    now = now or datetime.now(timezone.utc)
    stale_official_h = None
    for source, field, max_age_h, max_km in TIERS:
        best = None
        for sid in area.get(field, []):
            try:
                st = openaq.station(sid)
            except SourceError as e:
                log.warning("station %s unavailable: %s", sid, e)
                continue
            if st.get("lat") is None or st.get("lon") is None:
                continue
            dist = haversine_km(area["lat"], area["lon"], st["lat"], st["lon"])
            if dist > max_km:
                continue
            reading, age = _fresh_reading(st, now, max_age_h)
            if reading is None:
                if source == "official" and age is not None:
                    stale_official_h = age if stale_official_h is None else min(stale_official_h, age)
                continue
            if best is None or dist < best["distanceKm"]:
                best = {**reading, "source": source, "stationId": sid, "stationName": st["name"],
                        "distanceKm": round(dist, 1)}
        if best:
            best["staleOfficialAgeHours"] = None if stale_official_h is None else round(stale_official_h, 1)
            return best
    comps, ts = model_fn()
    return {"source": "model", "components": comps, "ts": ts, "stationId": None, "stationName": None,
            "distanceKm": None,
            "staleOfficialAgeHours": None if stale_official_h is None else round(stale_official_h, 1)}
