import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "areas.json")
_AREAS = None


def load_areas():
    global _AREAS
    if _AREAS is None:
        with open(_PATH, encoding="utf-8") as f:
            _AREAS = json.load(f)
    return _AREAS


def get_area(area_id):
    return next((a for a in load_areas() if a["areaId"] == area_id), None)
