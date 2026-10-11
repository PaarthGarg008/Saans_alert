"""Builds frontend/demo.js: a RECORDED sample (official readings from ~7 Oct 2026 plus fresh community sensors) so the UI works offline and for the demo video.
Everything is labelled 'recorded sample' in the UI; nothing here is presented as live."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from common.advice import ADVICE, DISCLAIMER, PROFILES        # noqa: E402
from common.aqi import compute_aqi                              # noqa: E402
from common.areas import get_area                               # noqa: E402

# areaId: (source, station name, pm2_5, pm10)  -- values from guide section 10.6
SAMPLE = {
    # official: PM2.5 timestamps confirmed ~88 h old on 11 Oct 2026 (per-sensor check in cli.py)
    "anand-vihar": ("official", "Anand Vihar, New Delhi - DPCC", 64, 222),
    "connaught-place": ("official", "ITO, New Delhi - CPCB", 63, 141),
    "narela": ("official", "Narela, Delhi - DPCC", 67, 269),
    "wazirpur": ("official", "Wazirpur, Delhi - DPCC", 51, 299),
    # community sensors, fresh on 11 Oct 2026
    "vasant-kunj": ("community", "Santushti Apartments, Vasant Kunj", 50.5, None),
    "greater-kailash": ("community", "GK1 Oberoi Terrace", 62.5, 238),
}

areas, data = [], {}
for aid, (src, name, pm25, pm10) in SAMPLE.items():
    a = get_area(aid)
    comps = {"pm2_5": pm25, **({"pm10": pm10} if pm10 else {})}
    res = compute_aqi(comps)
    areas.append({"areaId": aid, "name": a["name"]})
    data[aid] = {
        "area": {"areaId": aid, "name": a["name"]},
        "current": {**{k: res[k] for k in ("aqi", "category", "dominant", "tier", "used")}, "components": comps},
        "source": {"type": src, "stationName": name, "distanceKm": None, "staleOfficialAgeHours": None},
        "ageMinutes": 87 * 60 if src == "official" else 40, "stale": src == "official",
        "outlook": [], "recorded": True,
        "adviceAll": {p: {l: ADVICE[l][p][res["tier"]] for l in ("en", "hi")} for p in PROFILES},
    }
out = {"areas": areas, "data": data, "disclaimer": DISCLAIMER}
path = os.path.join(os.path.dirname(__file__), "..", "frontend", "demo.js")
with open(path, "w", encoding="utf-8") as f:
    f.write("window.DEMO = " + json.dumps(out, ensure_ascii=False) + ";\n")
print(f"wrote {path}: {len(areas)} areas")