from datetime import datetime, timedelta, timezone

from common.selector import haversine_km, pick_reading
from common.sources import SourceError

NOW = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
AREA = {"areaId": "t", "name": "T", "lat": 28.60, "lon": 77.20,
        "officialStationIds": [1, 2], "sensorIds": [3]}


def st(lat, lon, pm25_age_h, pm25=100.0, pm10=200.0, pm10_age_h=None, name="S"):
    return {"name": name, "lat": lat, "lon": lon,
            "pm25": (pm25, NOW - timedelta(hours=pm25_age_h)) if pm25_age_h is not None else None,
            "pm10": (pm10, NOW - timedelta(hours=pm10_age_h if pm10_age_h is not None else pm25_age_h))
            if pm25_age_h is not None and pm10 is not None else None}


class Fake:
    def __init__(self, data):
        self.data = data

    def station(self, i):
        v = self.data[i]
        if isinstance(v, Exception):
            raise v
        return v


MODEL = lambda: ({"pm2_5": 55.0, "pm10": 90.0, "no2": 10}, 1700000000)  # noqa: E731


def test_haversine_known_distance():
    assert haversine_km(28.6139, 77.2090, 28.7041, 77.1025) == pytest.approx(14.44, abs=0.1)


def test_fresh_official_wins():
    r = pick_reading(AREA, Fake({1: st(28.61, 77.21, 0.5, name="A"), 2: st(28.65, 77.25, 0.2), 3: st(28.6, 77.2, 0.1)}),
                     MODEL, NOW)
    assert (r["source"], r["stationId"]) == ("official", 1) and r["components"]["pm10"] == 200.0


def test_nearest_of_fresh_official():
    r = pick_reading(AREA, Fake({1: st(28.65, 77.25, 0.5), 2: st(28.61, 77.21, 0.5), 3: None}), MODEL, NOW)
    assert r["stationId"] == 2


def test_stale_official_is_never_used_falls_to_community():
    r = pick_reading(AREA, Fake({1: st(28.61, 77.21, 87.2), 2: st(28.62, 77.2, 87.2), 3: st(28.61, 77.2, 0.7, pm10=None)}),
                     MODEL, NOW)
    assert r["source"] == "community" and r["staleOfficialAgeHours"] == 87.2


def test_everything_stale_falls_back_to_model_and_reports_stale_age():
    r = pick_reading(AREA, Fake({1: st(28.61, 77.21, 87.2), 2: SourceError("boom"), 3: st(28.61, 77.2, 5)}), MODEL, NOW)
    assert r["source"] == "model" and r["staleOfficialAgeHours"] == 87.2 and r["components"]["no2"] == 10


def test_far_station_ignored():
    r = pick_reading(AREA, Fake({1: st(28.9, 77.2, 0.1), 2: st(28.9, 77.3, 0.1), 3: st(28.9, 77.3, 0.1)}), MODEL, NOW)
    assert r["source"] == "model"


def test_missing_pm25_is_rejected_and_old_pm10_dropped():
    no_pm25 = {"name": "x", "lat": 28.6, "lon": 77.2, "pm25": None, "pm10": (150.0, NOW)}
    r = pick_reading(AREA, Fake({1: no_pm25, 2: st(28.61, 77.2, 0.5, pm10_age_h=10), 3: None}), MODEL, NOW)
    assert r["stationId"] == 2 and "pm10" not in r["components"]


def test_future_timestamp_rejected():
    r = pick_reading(AREA, Fake({1: st(28.6, 77.2, -2), 2: st(28.6, 77.2, -2), 3: st(28.6, 77.2, -2)}), MODEL, NOW)
    assert r["source"] == "model"


import pytest  # noqa: E402
