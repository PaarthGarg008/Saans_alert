import pytest
from common.advice import ADVICE, PROFILES
from common.aqi import compute_aqi, sub_index


@pytest.mark.parametrize("pol,conc,idx", [("pm2_5", 30, 50), ("pm2_5", 60, 100), ("pm2_5", 90, 200),
                                          ("pm2_5", 120, 300), ("pm2_5", 250, 400), ("pm2_5", 380, 500),
                                          ("pm10", 50, 50), ("pm10", 100, 100), ("pm10", 250, 200),
                                          ("pm10", 350, 300), ("pm10", 430, 400), ("pm10", 550, 500)])
def test_breakpoints(pol, conc, idx):
    assert sub_index(pol, conc) == pytest.approx(idx)


def test_above_scale_is_500():
    assert sub_index("pm2_5", 900) == 500


@pytest.mark.parametrize("pm25,pm10,aqi,cat", [(238, 345, 391, "Very Poor"), (266, 403, 412, "Severe"),
                                               (47, None, 78, "Satisfactory"), (64, 222, 181, "Moderate"),
                                               (67, 269, 219, "Poor")])
def test_matches_guide_table(pm25, pm10, aqi, cat):
    comps = {"pm2_5": pm25, **({"pm10": pm10} if pm10 else {})}
    r = compute_aqi(comps)
    assert (r["aqi"], r["category"]) == (aqi, cat)


def test_dominant_and_used():
    r = compute_aqi({"pm2_5": 40, "pm10": 300, "no2": 99})
    assert r["dominant"] == "pm10" and r["used"] == ["pm10", "pm2_5"]


@pytest.mark.parametrize("bad", [{}, {"pm2_5": -5}, {"pm2_5": None}, {"pm2_5": "x"}, {"pm2_5": 99999}, None])
def test_invalid_input_rejected(bad):
    with pytest.raises(ValueError):
        compute_aqi(bad)


def test_glitch_value_ignored_but_other_pm_used():
    assert compute_aqi({"pm2_5": 99999, "pm10": 80})["dominant"] == "pm10"


def test_advice_complete():
    for lang in ("en", "hi"):
        for p in PROFILES:
            assert len(ADVICE[lang][p]) == 4 and all(ADVICE[lang][p])
