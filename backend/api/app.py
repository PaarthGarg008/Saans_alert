"""HTTP API (API Gateway v2 payload).  GET /areas, GET /areas/{areaId}, GET /areas/{areaId}/history, POST /subscribe"""
import base64
import json
import os
import re
import time
from datetime import datetime, timezone

from common import notify
from common.advice import DISCLAIMER, PROFILES, get_advice
from common.areas import get_area, load_areas
from common.ddb import from_ddb

STALE_MINUTES = 180
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
_table = None


def _readings():
    global _table
    if _table is None:
        import boto3
        _table = boto3.resource("dynamodb").Table(os.environ["READINGS_TABLE"])
    return _table


def _latest(area_id):
    from boto3.dynamodb.conditions import Key
    r = _readings().query(KeyConditionExpression=Key("areaId").eq(area_id), ScanIndexForward=False, Limit=1)
    return from_ddb(r["Items"][0]) if r["Items"] else None


def _history(area_id, hours):
    from boto3.dynamodb.conditions import Key
    since = int(time.time()) - hours * 3600
    r = _readings().query(KeyConditionExpression=Key("areaId").eq(area_id) & Key("ts").gte(since))
    return [from_ddb(i) for i in r["Items"]]


def respond(status, body, max_age=0):
    return {"statusCode": status,
            "headers": {"Content-Type": "application/json; charset=utf-8", "Cache-Control": f"max-age={max_age}"},
            "body": json.dumps(body, ensure_ascii=False)}


def _q(event, name, default):
    return (event.get("queryStringParameters") or {}).get(name, default)


def area_payload(area, item, profile, lang, now=None):
    now = now or time.time()
    age_min = max(0, int((now - item["readingTs"]) / 60))
    return {
        "area": {"areaId": area["areaId"], "name": area["name"]},
        "current": {k: item[k] for k in ("aqi", "category", "dominant", "tier", "used", "components")},
        "source": {"type": item["source"], "stationId": item.get("stationId"),
                   "stationName": item.get("stationName"), "distanceKm": item.get("distanceKm"),
                   "staleOfficialAgeHours": item.get("staleOfficialAgeHours")},
        "ageMinutes": age_min, "stale": age_min > STALE_MINUTES,
        "outlook": item.get("outlook", []),
        "profile": profile, "lang": lang, "advice": get_advice(profile, item["tier"], lang),
        "updatedAt": datetime.fromtimestamp(item["readingTs"], timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER[lang],
    }


def _body(event):
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw)


def subscribe(event):
    try:
        data = _body(event)
        email = str(data.get("email", "")).strip().lower()
        area_id, profile, lang = data.get("areaId"), data.get("profile"), data.get("language", "en")
    except (ValueError, AttributeError):
        return respond(400, {"error": "invalid JSON body"})
    if not EMAIL_RE.match(email):
        return respond(400, {"error": "invalid email"})
    if not get_area(area_id):
        return respond(400, {"error": "unknown areaId"})
    if profile not in PROFILES:
        return respond(400, {"error": "unknown profile"})
    if lang not in ("en", "hi"):
        return respond(400, {"error": "language must be en or hi"})
    notify.subscribe(email, area_id, profile, lang)
    return respond(202, {"message": "Check your inbox and confirm the subscription."})


def handler(event, context=None):
    route = event.get("routeKey", "")
    params = event.get("pathParameters") or {}
    try:
        if route == "GET /areas":
            return respond(200, [{"areaId": a["areaId"], "name": a["name"], "lat": a["lat"], "lon": a["lon"]}
                                 for a in load_areas()], max_age=3600)
        if route == "POST /subscribe":
            return subscribe(event)
        if route in ("GET /areas/{areaId}", "GET /areas/{areaId}/history"):
            area = get_area(params.get("areaId"))
            if not area:
                return respond(404, {"error": "unknown area"})
            if route.endswith("/history"):
                try:
                    hours = min(72, max(1, int(_q(event, "hours", 24))))
                except ValueError:
                    return respond(400, {"error": "hours must be a number"})
                return respond(200, [{"ts": i["ts"], "aqi": i["aqi"], "category": i["category"],
                                      "source": i["source"]} for i in _history(area["areaId"], hours)], 60)
            profile, lang = _q(event, "profile", "healthy"), _q(event, "lang", "en")
            if profile not in PROFILES:
                return respond(400, {"error": f"profile must be one of {PROFILES}"})
            lang = lang if lang in ("en", "hi") else "en"
            item = _latest(area["areaId"])
            if not item:
                return respond(404, {"error": "no reading yet for this area"})
            return respond(200, area_payload(area, item, profile, lang), 60)
        return respond(404, {"error": "not found"})
    except Exception:
        import logging
        logging.getLogger().exception("unhandled error")
        return respond(500, {"error": "internal error"})
