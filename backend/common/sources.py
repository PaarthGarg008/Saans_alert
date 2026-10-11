"""Data fetchers (stdlib only, so Lambda needs no extra packages): OpenWeatherMap + OpenAQ v3."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

OWM_URL = "https://api.openweathermap.org/data/2.5/air_pollution"
OPENAQ_URL = "https://api.openaq.org/v3/locations"


class SourceError(Exception):
    pass


def http_json(url, params=None, headers=None, timeout=10, retries=3):
    """GET -> parsed JSON. Retries 429/5xx and network errors. Never puts the query string (API key) in errors."""
    base = url
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers or {})
    for attempt in range(retries):
        last = attempt == retries - 1
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and not last:
                time.sleep(2 * (attempt + 1))
                continue
            raise SourceError(f"HTTP {e.code} from {base}") from e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if not last:
                time.sleep(1)
                continue
            raise SourceError(f"network/parse error from {base}: {e}") from e
    raise SourceError(f"failed: {base}")


# ---------- OpenWeatherMap (modelled data, any lat/lon) ----------
def owm_current(lat, lon, key):
    d = http_json(OWM_URL, {"lat": lat, "lon": lon, "appid": key})
    try:
        item = d["list"][0]
        return item["components"], int(item["dt"])
    except (KeyError, IndexError, TypeError) as e:
        raise SourceError("unexpected OpenWeatherMap payload") from e


def owm_forecast(lat, lon, key, hours=24):
    d = http_json(f"{OWM_URL}/forecast", {"lat": lat, "lon": lon, "appid": key})
    now = time.time()
    rows = [{"ts": int(i["dt"]), "components": i["components"]}
            for i in d.get("list", []) if i.get("dt", 0) >= now - 1800]
    return rows[:hours]


# ---------- OpenAQ v3 (measured data) ----------
def parse_dt(v):
    s = v.get("utc") if isinstance(v, dict) else v
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def _is_ugm3(units):
    if not units:
        return True  # unit not reported; accept
    return units.lower().replace("µ", "u").replace("μ", "u").replace("³", "3") == "ug/m3"


class OpenAQ:
    """Fetches one station's metadata + latest PM2.5/PM10. Results cached per instance (cache by station, not area)."""

    def __init__(self, key, pause=0.3):
        self.headers = {"X-API-Key": key}
        self.pause = pause
        self._cache = {}

    def station(self, loc_id):
        if loc_id not in self._cache:
            try:
                self._cache[loc_id] = self._fetch(loc_id)
            except SourceError as e:
                self._cache[loc_id] = e
        hit = self._cache[loc_id]
        if isinstance(hit, SourceError):
            raise hit
        return hit

    def _fetch(self, loc_id):
        meta = http_json(f"{OPENAQ_URL}/{loc_id}", headers=self.headers)
        time.sleep(self.pause)
        latest = http_json(f"{OPENAQ_URL}/{loc_id}/latest", headers=self.headers)
        time.sleep(self.pause)
        res = (meta.get("results") or [None])[0]
        if not res:
            raise SourceError(f"OpenAQ location {loc_id} not found")
        sensors = {s["id"]: (s.get("parameter") or {}) for s in res.get("sensors", [])}
        vals = {}
        for it in latest.get("results", []):
            p = sensors.get(it.get("sensorsId"), {})
            name = p.get("name")
            if name not in ("pm25", "pm10") or it.get("value") is None or not _is_ugm3(p.get("units")):
                continue
            when = parse_dt(it.get("datetime"))
            if when:
                vals[name] = (float(it["value"]), when)
        c = res.get("coordinates") or {}
        return {"id": loc_id, "name": res.get("name"), "lat": c.get("latitude"),
                "lon": c.get("longitude"), "pm25": vals.get("pm25"), "pm10": vals.get("pm10")}
