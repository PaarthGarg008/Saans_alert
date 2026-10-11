"""Alert rules (guide 9.4): alert when an area WORSENS into Poor or beyond; never repeat the same
category within 12 h; send "improved" only when the category drops."""
from .advice import ADVICE, CATEGORY_HI, DISCLAIMER, PROFILES, get_advice
from .aqi import CATEGORY_ORDER

POOR = CATEGORY_ORDER.index("Poor")
COOLDOWN_S = 12 * 3600


def decide(prev_cat, alerted_cat, alerted_at, cat, now_ts):
    """-> 'worse' | 'improved' | None.  prev_cat = last observed category (None on first run)."""
    ci = CATEGORY_ORDER.index(cat)
    pi = CATEGORY_ORDER.index(prev_cat) if prev_cat in CATEGORY_ORDER else -1
    if ci >= POOR and ci > pi:
        if alerted_cat == cat and alerted_at and now_ts - alerted_at < COOLDOWN_S:
            return None
        return "worse"
    if pi >= POOR and ci < pi:
        return "improved"
    return None


def source_text(reading, lang):
    if reading["source"] == "model":
        return "अनुमान (मॉडल डेटा)" if lang == "hi" else "Estimated from model data"
    kind = {"official": ("Official station", "सरकारी स्टेशन"),
            "community": ("Community sensor", "सामुदायिक सेंसर")}[reading["source"]][lang == "hi"]
    return f"{kind}: {reading['stationName']}, {reading['distanceKm']} km"


def build_messages(area, result, reading, kind):
    """-> list of {profile, lang, subject, body}, one per profile x language."""
    out = []
    for lang in ("en", "hi"):
        cat = CATEGORY_HI[result["category"]] if lang == "hi" else result["category"]
        for profile in PROFILES:
            if kind == "worse":
                subject = (f"SaansAlert: {cat} air in {area['name']} (AQI {result['aqi']})" if lang == "en"
                           else f"साँसअलर्ट: {area['name']} में हवा {cat} (AQI {result['aqi']})")
                head = (f"{area['name']} air is now {cat} (estimated AQI {result['aqi']})." if lang == "en"
                        else f"{area['name']} में हवा अब {cat} है (अनुमानित AQI {result['aqi']})।")
            else:
                subject = (f"SaansAlert: air improving in {area['name']}" if lang == "en"
                           else f"साँसअलर्ट: {area['name']} में हवा बेहतर हुई")
                head = (f"{area['name']} air has improved to {cat} (estimated AQI {result['aqi']})." if lang == "en"
                        else f"{area['name']} में हवा सुधरकर {cat} हुई (अनुमानित AQI {result['aqi']})।")
            body = "\n\n".join([head, get_advice(profile, result["tier"], lang),
                                source_text(reading, lang), DISCLAIMER[lang]])
            out.append({"profile": profile, "lang": lang, "subject": subject[:100], "body": body})
    return out
