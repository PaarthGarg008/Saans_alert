"""Estimated Indian (CPCB-style) AQI from raw PM2.5 / PM10 concentrations (ug/m3).

AQI = highest sub-index; the pollutant that produced it is the "dominant" one.
Official CPCB AQI uses 24-hour averages; we use the latest reading, so every
number shown to users is labelled "estimated".
"""

# (conc_low, conc_high, index_low, index_high), ug/m3.  Matches CPCB's published
# bands: PM2.5 30/60/90/120/250, PM10 50/100/250/350/430.
BREAKPOINTS = {
    "pm2_5": [(0, 30, 0, 50), (30, 60, 50, 100), (60, 90, 100, 200),
              (90, 120, 200, 300), (120, 250, 300, 400), (250, 380, 400, 500)],
    "pm10": [(0, 50, 0, 50), (50, 100, 50, 100), (100, 250, 100, 200),
             (250, 350, 200, 300), (350, 430, 300, 400), (430, 550, 400, 500)],
}
# Anything above these is treated as a sensor glitch and ignored.
SANE_MAX = {"pm2_5": 1500.0, "pm10": 3000.0}

CATEGORIES = [(50, "Good"), (100, "Satisfactory"), (200, "Moderate"),
              (300, "Poor"), (400, "Very Poor"), (500, "Severe")]
CATEGORY_ORDER = [name for _, name in CATEGORIES]


def sub_index(pollutant, conc):
    for lo, hi, ilo, ihi in BREAKPOINTS[pollutant]:
        if conc <= hi:
            return ilo + (conc - lo) * (ihi - ilo) / (hi - lo)
    return 500.0


def clean(components):
    """Keep only valid PM values: numeric, non-negative, below the sanity cap."""
    out = {}
    for p, cap in SANE_MAX.items():
        v = (components or {}).get(p)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= cap:
            out[p] = float(v)
    return out


def tier_for(aqi):
    """0 Good/Satisfactory, 1 Moderate, 2 Poor, 3 Very Poor/Severe."""
    return 0 if aqi <= 100 else 1 if aqi <= 200 else 2 if aqi <= 300 else 3


def category_for(aqi):
    return next(name for limit, name in CATEGORIES if aqi <= limit)


def compute_aqi(components):
    """-> dict(aqi, category, dominant, tier, used). Raises ValueError if no valid PM value."""
    pm = clean(components)
    if not pm:
        raise ValueError("no valid PM2.5/PM10 value")
    subs = {p: sub_index(p, c) for p, c in pm.items()}
    dominant = max(subs, key=subs.get)
    aqi = round(subs[dominant])
    return {"aqi": aqi, "category": category_for(aqi), "dominant": dominant,
            "tier": tier_for(aqi), "used": sorted(pm)}
