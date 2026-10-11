"""Scheduled ingest: for every area pick the best fresh source, compute AQI, store, and fire alerts."""
import logging
import os
import time

from common import alerts, notify
from common.aqi import compute_aqi
from common.areas import load_areas
from common.config import openaq_key, owm_key
from common.ddb import to_ddb
from common.selector import pick_reading
from common.sources import OpenAQ, SourceError, owm_current, owm_forecast

log = logging.getLogger()
log.setLevel(logging.INFO)
TTL_S = 7 * 24 * 3600


def _outlook(area, key):
    try:
        rows = owm_forecast(area["lat"], area["lon"], key)
    except SourceError as e:
        log.warning("forecast failed for %s: %s", area["areaId"], e)
        return []
    out = []
    for r in rows:
        try:
            a = compute_aqi(r["components"])
        except ValueError:
            continue
        out.append({"ts": r["ts"], "aqi": a["aqi"], "category": a["category"]})
    return out


def process_area(area, openaq, owm, tables, now_ts, send_alerts=True):
    reading = pick_reading(area, openaq, lambda: owm_current(area["lat"], area["lon"], owm))
    result = compute_aqi(reading["components"])
    item = {"areaId": area["areaId"], "ts": now_ts, "readingTs": reading["ts"], **result,
            "components": reading["components"], "source": reading["source"],
            "stationId": reading["stationId"], "stationName": reading["stationName"],
            "distanceKm": reading["distanceKm"], "staleOfficialAgeHours": reading["staleOfficialAgeHours"],
            "outlook": _outlook(area, owm), "ttl": now_ts + TTL_S}
    tables["readings"].put_item(Item=to_ddb(item))
    if send_alerts:
        _alert(area, result, reading, tables["state"], now_ts)
    return item


def _alert(area, result, reading, state_table, now_ts):
    st = state_table.get_item(Key={"areaId": area["areaId"]}).get("Item", {})
    kind = alerts.decide(st.get("category"), st.get("alertedCategory"),
                         int(st["alertedAt"]) if st.get("alertedAt") else None, result["category"], now_ts)
    new = {"areaId": area["areaId"], "category": result["category"],
           "alertedCategory": st.get("alertedCategory"), "alertedAt": st.get("alertedAt")}
    if kind:
        notify.publish_all(area["areaId"], alerts.build_messages(area, result, reading, kind))
        new.update(alertedCategory=result["category"], alertedAt=now_ts)
        log.info("alert %s sent for %s (%s)", kind, area["areaId"], result["category"])
    state_table.put_item(Item=to_ddb(new))


def handler(event, context):
    import boto3
    ddb = boto3.resource("dynamodb")
    tables = {"readings": ddb.Table(os.environ["READINGS_TABLE"]),
              "state": ddb.Table(os.environ["STATE_TABLE"])}
    owm, aq = owm_key(), OpenAQ(openaq_key())
    now_ts, ok, failed = int(time.time()), 0, []
    for area in load_areas():
        try:
            item = process_area(area, aq, owm, tables, now_ts)
            ok += 1
            log.info("%s -> AQI %s %s via %s", area["areaId"], item["aqi"], item["category"], item["source"])
        except Exception:                       # one bad area must not stop the rest
            log.exception("area %s failed", area["areaId"])
            failed.append(area["areaId"])
    return {"ok": ok, "failed": failed}
