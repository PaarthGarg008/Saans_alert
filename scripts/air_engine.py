"""
air_engine.py - area-level air quality + health-profile advice.
Drop next to your weather.py. Uses the same OPENWEATHER_API_KEY.

Idea: OpenWeatherMap's Air Pollution API returns raw pollutant
concentrations (pm2_5, pm10, no2, o3, so2, co) for ANY lat/lon.
Your current code only reads the coarse 1-5 "aqi" field and throws the
rest away. Here we use the raw numbers and compute an Indian (CPCB-style)
AQI ourselves.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Approximate centre points of Delhi localities (verify/extend as needed).
AREAS = {
    "Anand Vihar": (28.6469, 77.3164),
    "Rohini": (28.7324, 77.1177),
    "RK Puram": (28.5633, 77.1869),
    "Dwarka": (28.5921, 77.0460),
    "Connaught Place": (28.6315, 77.2167),
    "Okhla": (28.5308, 77.2710),
    "Punjabi Bagh": (28.6683, 77.1167),
    "Mayur Vihar": (28.6075, 77.2937),
    "Narela": (28.8527, 77.0929),
}

# (conc_low, conc_high, index_low, index_high) - CPCB-style breakpoints, ug/m3.
# Simplified to be continuous; check against the official CPCB table before final.
BREAKPOINTS = {
    "pm2_5": [(0, 30, 0, 50), (30, 60, 50, 100), (60, 90, 100, 200),
              (90, 120, 200, 300), (120, 250, 300, 400), (250, 380, 400, 500)],
    "pm10": [(0, 50, 0, 50), (50, 100, 50, 100), (100, 250, 100, 200),
             (250, 350, 200, 300), (350, 430, 300, 400), (430, 550, 400, 500)],
}

CATEGORIES = [(50, "Good"), (100, "Satisfactory"), (200, "Moderate"),
              (300, "Poor"), (400, "Very Poor"), (500, "Severe")]


def sub_index(pollutant, conc):
    for lo, hi, ilo, ihi in BREAKPOINTS[pollutant]:
        if conc <= hi:
            return ilo + (conc - lo) * (ihi - ilo) / (hi - lo)
    return 500


def cpcb_aqi(components):
    """Returns (aqi, category, dominant_pollutant, tier 0-3)."""
    subs = {p: sub_index(p, components[p]) for p in BREAKPOINTS if p in components}
    dominant = max(subs, key=subs.get)
    aqi = round(subs[dominant])
    category = next(name for limit, name in CATEGORIES if aqi <= limit)
    tier = 0 if aqi <= 100 else 1 if aqi <= 200 else 2 if aqi <= 300 else 3
    return aqi, category, dominant, tier


def get_components(lat, lon):
    r = requests.get(
        "https://api.openweathermap.org/data/2.5/air_pollution",
        params={"lat": lat, "lon": lon, "appid": API_KEY}, timeout=10)
    r.raise_for_status()
    return r.json()["list"][0]["components"]


# Tier: 0 = Good/Satisfactory, 1 = Moderate, 2 = Poor, 3 = Very Poor/Severe
# General precautionary guidance, NOT medical advice.
ADVICE = {
    "healthy adult": [
        "Air is fine. Normal activity.",
        "Fine for most; very sensitive people may notice irritation.",
        "Cut back on long or intense outdoor exercise. Prefer a mask outdoors.",
        "Avoid outdoor exercise. Wear an N95/FFP2 mask if you must go out."],
    "asthma / COPD": [
        "Normal activity. Keep your reliever inhaler with you as usual.",
        "Limit long outdoor exertion. Keep your reliever inhaler handy.",
        "Stay mostly indoors, avoid exercise outside, wear N95 outdoors. Follow your doctor's action plan.",
        "Stay indoors with windows closed. Follow your doctor's action plan; seek care if symptoms worsen."],
    "heart condition": [
        "Normal activity.",
        "Avoid heavy exertion outdoors.",
        "Avoid outdoor exertion; wear N95 outdoors. Report chest discomfort or breathlessness.",
        "Stay indoors. Seek medical help for chest pain, palpitations or severe breathlessness."],
    "child": [
        "Outdoor play is fine.",
        "Shorten intense outdoor play.",
        "Indoor activities for PE/play; N95-type mask (child fit) if travelling.",
        "Keep children indoors. Skip outdoor assembly/PE."],
    "elderly": [
        "Normal activity.",
        "Prefer shorter walks, avoid peak traffic hours.",
        "Avoid outdoor walks; wear N95 if you must go out.",
        "Stay indoors with windows closed. Check in on older family members."],
    "pregnant": [
        "Normal activity.",
        "Limit long time near busy roads.",
        "Avoid outdoor exertion; wear N95 outdoors.",
        "Stay indoors; speak to your doctor if you feel unwell."],
    "outdoor worker": [
        "Normal work.",
        "Take regular breaks away from traffic and dust.",
        "Wear N95 on the job; rotate tasks and take indoor breaks.",
        "Wear N95, minimise outdoor hours, and ask about shifting work times."],
}


def report(area, profile):
    lat, lon = AREAS[area]
    comp = get_components(lat, lon)
    aqi, category, dominant, tier = cpcb_aqi(comp)
    print(f"\n===== {area}, Delhi =====")
    print(f"PM2.5: {comp['pm2_5']} ug/m3 | PM10: {comp['pm10']} ug/m3 | "
          f"NO2: {comp['no2']} | O3: {comp['o3']} | SO2: {comp['so2']} | CO: {comp['co']}")
    print(f"Estimated AQI: {aqi} ({category}), driven by {dominant}")
    print(f"For {profile}: {ADVICE[profile][tier]}\n")


def pick(options, label):
    keys = list(options)
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {k}")
    return keys[int(input(f"{label} (number): ")) - 1]


if __name__ == "__main__":
    area = pick(AREAS, "Area")
    profile = pick(ADVICE, "Health profile")
    report(area, profile)
