import json
import time

from api import app
from common import alerts
from common.areas import get_area
from common.advice import PROFILES

H = 3600


def test_alert_rules():
    now = 10_000_000
    assert alerts.decide(None, None, None, "Poor", now) == "worse"
    assert alerts.decide("Moderate", None, None, "Poor", now) == "worse"
    assert alerts.decide("Poor", "Poor", now - H, "Poor", now) is None          # same, no escalation
    assert alerts.decide("Poor", "Poor", now - H, "Very Poor", now) == "worse"  # escalation
    assert alerts.decide("Moderate", "Poor", now - 2 * H, "Poor", now) is None  # 12h cooldown, same category
    assert alerts.decide("Moderate", "Poor", now - 13 * H, "Poor", now) == "worse"
    assert alerts.decide("Poor", "Poor", now - H, "Moderate", now) == "improved"
    assert alerts.decide("Good", None, None, "Satisfactory", now) is None
    assert alerts.decide("Moderate", None, None, "Good", now) is None


def test_messages_cover_all_profiles_and_languages():
    area = get_area("rohini")
    res = {"aqi": 391, "category": "Very Poor", "tier": 3}
    reading = {"source": "official", "stationName": "Rohini, Delhi - DPCC", "distanceKm": 2.1}
    msgs = alerts.build_messages(area, res, reading, "worse")
    assert len(msgs) == 2 * len(PROFILES) and all(len(m["subject"]) <= 100 for m in msgs)
    assert any("Not medical advice" in m["body"] for m in msgs)


ITEM = {"areaId": "rohini", "ts": 1, "readingTs": int(time.time()) - 600, "aqi": 391, "category": "Very Poor",
        "dominant": "pm2_5", "tier": 3, "used": ["pm10", "pm2_5"], "components": {"pm2_5": 238.0},
        "source": "community", "stationId": 9, "stationName": "X", "distanceKm": 2.0, "outlook": []}


def ev(route, path=None, qs=None, body=None):
    return {"routeKey": route, "pathParameters": path, "queryStringParameters": qs,
            "body": json.dumps(body) if body is not None else None}


def test_area_endpoint(monkeypatch):
    monkeypatch.setattr(app, "_latest", lambda a: ITEM)
    r = app.handler(ev("GET /areas/{areaId}", {"areaId": "rohini"}, {"profile": "asthma", "lang": "hi"}))
    b = json.loads(r["body"])
    assert r["statusCode"] == 200 and b["current"]["aqi"] == 391 and b["stale"] is False
    assert "इंडोर" not in b["advice"] and "घर के अंदर" in b["advice"] and b["source"]["type"] == "community"


def test_errors(monkeypatch):
    monkeypatch.setattr(app, "_latest", lambda a: None)
    assert app.handler(ev("GET /areas/{areaId}", {"areaId": "nope"}))["statusCode"] == 404
    assert app.handler(ev("GET /areas/{areaId}", {"areaId": "rohini"}, {"profile": "x"}))["statusCode"] == 400
    assert app.handler(ev("GET /areas/{areaId}", {"areaId": "rohini"}))["statusCode"] == 404   # no data yet
    assert app.handler(ev("GET /nothing"))["statusCode"] == 404


def test_stale_flag(monkeypatch):
    monkeypatch.setattr(app, "_latest", lambda a: {**ITEM, "readingTs": int(time.time()) - 5 * H})
    assert json.loads(app.handler(ev("GET /areas/{areaId}", {"areaId": "rohini"}))["body"])["stale"] is True


def test_list_areas():
    body = json.loads(app.handler(ev("GET /areas"))["body"])
    assert len(body) >= 20 and {"areaId", "name"} <= set(body[0])


def test_subscribe_validation_and_success(monkeypatch):
    calls = []
    monkeypatch.setattr(app.notify, "subscribe", lambda *a: calls.append(a))
    good = {"email": "A@b.in", "areaId": "rohini", "profile": "child", "language": "hi"}
    assert app.handler(ev("POST /subscribe", body=good))["statusCode"] == 202 and calls == [("a@b.in", "rohini", "child", "hi")]
    for bad in ({**good, "email": "nope"}, {**good, "areaId": "x"}, {**good, "profile": "x"}, {**good, "language": "fr"}):
        assert app.handler(ev("POST /subscribe", body=bad))["statusCode"] == 400
    assert app.handler({"routeKey": "POST /subscribe", "body": "{not json"})["statusCode"] == 400
