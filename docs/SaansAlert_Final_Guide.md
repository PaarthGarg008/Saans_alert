# SaansAlert: Final Project Guide (updated 11 Oct 2026)

**Area-level air quality + personalised health advice for Delhi-NCR, built on AWS.**

> This file is a complete, self-contained brief. Paste it into any AI assistant to continue the work. It contains the context, decisions, plain-language explanations, architecture, step-by-step plan, station-data integration plan, and the full code written so far (Appendices A and B).

---

## Table of Contents
1. Hackathon context and rules
2. Starting point: the existing CLI and its problems
3. The idea in plain language
4. Concepts explained (PM2.5, AQI, why the old number says little)
5. Scope: MVP, should-have, could-have, won't-do
6. Key design decisions
7. Architecture (with plain-language walkthrough)
8. Data model and API contract
9. Core logic specifications
10. Government station data (OpenAQ): plan, **real findings from 11 Oct 2026**, tiered source strategy, station shortlist
11. Step-by-step work plan (Phases 0-9)
12. Demo video script and blog outline
13. Risks and mitigations
14. Repo structure
15. Status log and open items (verified vs unverified)
16. Minimum viable checklist
17. Prompts to reuse with other AI assistants
- Appendix A: `air_engine.py`
- Appendix B: `list_delhi_stations.py`
- Appendix C: `check_station_freshness.py`

---

## 1. Hackathon context and rules

- Student hackathon with three tracks: **Air**, Heat and Water, Waste and Energy. We are building in **Track 01: Air** (pollution, exposure, stubble burning, indoor air, school safety on bad days).
- **Eligibility:** the project must use at least one **AWS open-source tool** (e.g., SAM CLI, LocalStack, Strands Agents SDK, Finch, EKS Distro, Firecracker, Corretto, OpenSearch, Cedar) **or be deployed on AWS** (Lambda, DynamoDB, S3, CloudFront, SNS, EventBridge, Bedrock, etc.). Both is fine. Other tools are allowed.
- **Mandatory:** verify student status on **AWS Builder Center** (free profile, no credit card).
- **Judging criteria:** (1) Idea and Impact, (2) Built on AWS, (3) Design and Usability, (4) Execution (does it work), (5) a **3-minute recorded demo video** (no live demo).
- **Judges' guidance:** a small problem solved well beats a big one solved vaguely. One feature that runs beats five that almost do.
- **Prizes and extras:** track winner cash plus AWS credits; top 10 students across tracks get fast-track Amazon interviews; runner-up teams get AWS credits; top blogs published on AWS Builder Center win prizes; tour swag for top teams.
- **Credits:** a new AWS account gets up to $200 free credits. Use them first; a $25 credit code can be requested from the organisers after that (one form per team, filled by the team leader). New-account verification accepts debit cards and RuPay.

---

## 2. Starting point: the existing CLI and its problems

A Python CLI (`weather.py`) using OpenWeatherMap's **Current Weather** and **Air Pollution** APIs.

**Features:** city search; temperature, feels-like, humidity, wind (km/h), condition; coarse AQI (1-5) with labels Good/Fair/Moderate/Poor/Very Poor; last-5 search history in `history.json` (successes and failures); handling of invalid city, network errors, API failures, missing/corrupt history file.

**Problems:**
1. It works per **city**, not per **area** inside a city.
2. It reads only the coarse `aqi` 1-5 field and **discards the raw pollutant concentrations** (pm2_5, pm10, no2, o3, so2, co, nh3) that the same API response already contains.
3. No personalisation, no forecast, no alerts, not hosted.
4. Minor code issues: the AQI request has no timeout and no error handling; the city name is used for display even if the API resolved a different place.

---

## 3. The idea in plain language

A single city-wide "AQI 4" for Delhi hides what is happening in your neighbourhood and says nothing about what **you** should do. SaansAlert fixes two things:

1. **Where:** readings for localities (Rohini, Anand Vihar, Dwarka, RK Puram...) instead of one number for the whole city.
2. **Who:** advice tailored to health profile: healthy adult, asthma/COPD, heart condition, child, elderly, pregnant, outdoor worker.

**Pitch line:** "Not just how bad the air is, but what it means for you, where you live."

**Secondary/stretch user:** school administrators who need a clear daily go/no-go for outdoor activity (Normal / Limit outdoor activity / Indoor only / Consider closure).

---

## 4. Concepts explained

- **PM2.5:** particles smaller than 2.5 micrometres. They go deep into the lungs and are usually the dominant pollutant in Delhi. **PM10** is the coarser dust fraction. Other pollutants: NO2 (traffic/combustion), O3 (ozone), SO2, CO.
- **AQI (Air Quality Index):** a single number from 0-500 summarising pollution. India's scale categories: Good (0-50), Satisfactory (51-100), Moderate (101-200), Poor (201-300), Very Poor (301-400), Severe (401-500).
- **How AQI is computed:** each pollutant's concentration is converted to a sub-index by linear interpolation inside a breakpoint band. The AQI is the **highest** sub-index, and that pollutant is the **dominant pollutant**.
- **Why OpenWeatherMap's 1-5 score is weak:** it is a coarse 5-level scale. Delhi sits at 4-5 for much of winter, so it cannot distinguish a bad day from a dangerous one. The raw concentrations can.
- **Instantaneous vs 24-hour average:** official AQI uses 24-hour averages for PM. OpenWeatherMap gives current values, so our number must be labelled **"estimated"**.
- **Modelled vs measured data:** OpenWeatherMap's pollution data is modelled on a coarse grid, so nearby areas may look similar. Government station data is **measured** with calibrated instruments, which is more credible.

---

## 5. Scope

**MVP (must work):** area picker; pollutant-based AQI; health-profile advice; hosted web page on AWS; scheduled data refresh.

**Should have:** 24-hour outlook; email alerts; Hindi/English toggle; government station data with fallback.

**Could have:** school mode; Bedrock-rephrased wording; map view; trend chart.

**Won't do:** medical diagnosis; user accounts/passwords; native mobile app; ML forecasting.

---

## 6. Key design decisions

| Decision | Choice | Reason |
|---|---|---|
| Baseline data source | OpenWeatherMap Air Pollution API (current + forecast) by lat/lon | Already in use, free tier, returns raw pollutants |
| Data source strategy | **Tiered:** (1) fresh government station, (2) fresh community sensor (clearly labelled), (3) OpenWeatherMap model estimate. A stale reading never drives health advice | Measured data beats modelled data only if it is fresh (see 10.6) |
| AQI | Compute our own Indian-style AQI from PM2.5/PM10 | OWM's 1-5 is too coarse for India |
| Advice engine | **Rule-based table** (profile x severity tier) | Predictable, explainable, safe. No AI-invented medical advice |
| AI usage (optional) | Bedrock/Strands only to rephrase or translate approved text | AWS/AI story without medical risk |
| IaC and local dev | **AWS SAM** (open source) + optional LocalStack | Satisfies "AWS open-source tool" rule |
| Backend | Python 3.12 Lambda | Reuses existing Python |
| Frontend | Static HTML/CSS/JS on S3 + CloudFront (or Amplify Hosting) | Fast, cheap, mobile friendly |
| Alerts | SNS email first; SMS optional or simulated | India SMS via SNS has registration requirements: verify before relying on it |

**Disclaimer to show in the app:** "General precautionary guidance based on estimated air quality. Not medical advice. Follow your doctor's plan."

---

## 7. Architecture

```
                 +-------------------+
 EventBridge --> |  Lambda: ingest   | --> OpenWeatherMap (current + forecast)
 (every 1-2 h)   |  (fetch+compute)  | --> OpenAQ (nearest government station)
                 +---------+---------+
                           |
                           v
                 +-------------------+          +---------------------+
                 |    DynamoDB       | <------> | Lambda: alert check |--> SNS --> email/SMS
                 | Readings, Areas,  |          | (threshold crossing)|
                 | Subscribers       |          +---------------------+
                 +---------+---------+
                           ^
                           |
                 +---------+---------+
 Browser  -----> | API Gateway (HTTP) | --> Lambda: api (area, advice, subscribe)
 (S3+CloudFront) +-------------------+

 Secrets: OpenWeatherMap + OpenAQ keys in SSM Parameter Store (SecureString)
 Monitoring: CloudWatch logs + billing alarm
 Optional: Bedrock inside api Lambda to rephrase/translate approved advice
```

### Plain-language walkthrough (the restaurant analogy)
- **EventBridge** = the alarm clock; wakes the system every hour or two.
- **Lambda ingest** = the cook; fetches fresh pollution data for each area, calculates AQI, stores it.
- **DynamoDB** = the pantry; holds areas, latest readings, subscribers.
- **API Gateway + Lambda api** = the waiter; when someone picks an area and profile, fetches the latest reading and matching advice.
- **S3 + CloudFront** = the shop front; serves the plain HTML/JS site.
- **SNS** = the messenger; emails subscribers when their area gets worse.
- **SSM Parameter Store** = the safe for API keys, so they never sit in code or GitHub.

Flow: alarm -> fetch and calculate -> store -> website asks -> advice shown -> alert sent if things worsen.

---

## 8. Data model and API contract

### DynamoDB tables
**Areas** (small, seeded once): `areaId` (PK, e.g. `anand-vihar`), `name`, `city`, `lat`, `lon`, `stationId` (optional OpenAQ location id), `stationDistanceKm` (optional).

**Readings:** `areaId` (PK), `ts` (SK, epoch seconds), `pm2_5`, `pm10`, `no2`, `o3`, `so2`, `co`, `aqi`, `category`, `dominant`, `source` (`station` | `owm`), `stationName` (optional), `isForecast` (bool), `ttl` (expire after ~7 days).

**Subscribers:** `email` (PK), `areaId`, `profile`, `language`, `lastAlertCategory`, `lastAlertAt`, `createdAt`.

### API
- `GET /areas` -> list of areas
- `GET /areas/{areaId}?profile=asthma` -> `{ current, outlook[], advice, source, updatedAt, disclaimer }`
- `GET /areas/{areaId}/history?hours=24` -> readings for a trend chart
- `POST /subscribe` body `{ email, areaId, profile, language }`

---

## 9. Core logic specifications

### 9.1 AQI computation
For PM2.5 and PM10: sub-index by linear interpolation within its band; AQI = max sub-index; dominant = argmax. Starter code is in Appendix A (`cpcb_aqi`). **The breakpoint table there is simplified; verify it against the official CPCB table before final.** Label results "estimated".

### 9.2 Severity tiers
Tier 0: Good/Satisfactory (AQI up to 100). Tier 1: Moderate (101-200). Tier 2: Poor (201-300). Tier 3: Very Poor/Severe (301+).

### 9.3 Advice table
Profiles x tiers = 28 short approved sentences (see `ADVICE` in Appendix A). Review them against reputable public guidance (CPCB / health-agency advisories). Keep language precautionary, never diagnostic.

### 9.4 Alert logic
- Alert only when the category **worsens** into Poor or beyond, or the 24h outlook shows it will.
- Store `lastAlertCategory`; do not resend the same category within 12 hours.
- Hysteresis: send an "improved" message only when the category drops a full tier.

### 9.5 Failure handling
- If a data call fails, serve the last reading with "last updated X minutes ago".
- Reading older than ~3 hours: show a stale-data warning, or fall back to the other source.
- Validate/clamp absurd values; log and skip bad records.
- Always set request timeouts; handle 401 / 429 / 5xx explicitly.

---

## 10. Government station data (OpenAQ) integration plan

### 10.1 What it is
Delhi has dozens of government monitoring stations (CPCB, DPCC). **OpenAQ** aggregates such data from government networks worldwide and serves it through one API. Each area is matched to its nearest station; if the station is missing or stale, fall back to OpenWeatherMap.

### 10.2 Verified facts (checked against OpenAQ's current docs)
- OpenAQ API **v3** requires an **API key on every request**, sent in the `X-API-Key` header. The key is free (register at explore.openaq.org; the key is in account settings).
- There is a **latest** resource giving the most recent measurement per sensor for a location, e.g. `/v3/locations/{id}/latest`, with fields including `datetime`, `value`, `coordinates`, `sensorsId`, `locationsId`.
- Some third-party tools claim no key is needed; trust the official docs and use a key.

### 10.3 Not yet verified
- (Resolved) `list_delhi_stations.py` and `check_station_freshness.py` both ran successfully against OpenAQ v3, so the location search, `/latest` endpoint, and sensor/parameter structure used by the scripts work.
- Rate limits and licence/attribution terms for publishing results (the scripts sleep 1 second between calls to stay safe).
- **Why the government feed is about 3.6 days old** (see 10.6): OpenAQ ingestion pause, upstream CPCB outage, or something else. Cause unknown.
- The CPCB real-time feed on data.gov.in (access and terms).
- Whether India SMS via SNS is workable for the project.

### 10.4 Integration steps
1. Get an OpenAQ key; add `OPENAQ_API_KEY` to `.env` (never commit or paste it).
2. Run Appendix B (`list_delhi_stations.py`). It sweeps five centre points and merges duplicates, printing station ID, name, coordinates, last-seen time, and pollutants measured; it saves `delhi_stations.json`.
3. Review the output: drop stations whose last-seen time is old; prefer stations reporting PM2.5 and PM10; note which planned areas have a station nearby.
4. Build the area-to-station mapping: for each area, compute the **haversine distance** to every eligible station and pick the nearest within a sensible cap (e.g. 5-8 km). Store `stationId` and `stationDistanceKm` in the Areas table (precompute once, do not recompute per request).
5. Write `station_source.py`: fetch `/v3/locations/{id}/latest`, extract latest PM2.5 and PM10 values with timestamps, check freshness (reject readings older than about 3 hours), return a components dict in the same shape as the OpenWeatherMap one.
6. In the ingest Lambda: try station first, otherwise OpenWeatherMap. Record `source`, `stationName`, and the reading time.
7. In the UI: show provenance, e.g. "Anand Vihar station, 4 km away, updated 20 min ago" or "Estimated (model data)".
8. Compare station vs OpenWeatherMap readings for 3 areas and keep the results for the blog and demo ("why we show the source").

### 10.6 Gotchas
- Stations go offline or report old data: freshness check and fallback are required.
- A station may not measure every pollutant: compute AQI from whatever PM values exist; show which were used.
- The nearest station can be far away: always display the distance.
- Units: confirm all values are in ug/m3 before using the AQI breakpoints (CO is usually mg/m3 or ug/m3 depending on source; we do not use it for the AQI).
- Do not exceed rate limits; one scheduled ingest every 1-2 hours for ~20 areas is light. Cache station results by station, not by area, since several areas can share a station.
- Add OpenAQ attribution per its terms.

### 10.6 Real findings from the first runs (11 October 2026)

**Run 1: `list_delhi_stations.py` found 110 stations** within the five sweep circles (includes Noida, Gurugram, Ghaziabad, Faridabad stations).
- **Duplicates:** many stations are registered 2-3 times (e.g. Anand Vihar, R K Puram, Punjabi Bagh, Rohini, Narela). Extra entries are old registrations last seen in 2018-2022. Always keep the entry with the newest data and ignore the rest.
- **Government stations (DPCC/CPCB/IMD/IITM)** mostly show last-seen **2026-10-07 ~14:30 UTC**, about four days before the run.
- **Fresh sources (updated 2026-10-11):** community/low-cost sensors (Air Check, Anand Lok, GK1 Oberoi Terrace, Santushti Apartments Vasant Kunj, Sector 1 Noida extension, a few others) and one PM2.5-only "New Delhi" entry.

**Run 2: `check_station_freshness.py`** confirmed that this is real, not a metadata quirk:

| Station | PM2.5 | PM10 | Age (hours) | Est. AQI |
|---|---|---|---|---|
| Anand Vihar (DPCC) | 64 | 222 | 87.2 | 181 Moderate |
| Rohini (DPCC) | 238 | 345 | 87.2 | 391 Very Poor |
| R K Puram (DPCC) | 201 | 339 | 87.2 | 362 Very Poor |
| Dwarka Sector 8 (DPCC) | 246 | 423 | 87.2 | 397 Very Poor |
| ITO (CPCB) | 63 | 141 | 87.2 | 127 Moderate |
| Okhla Phase-2 (DPCC) | 266 | 403 | 87.2 | 412 Severe |
| Punjabi Bagh (DPCC) | 183 | 322 | 87.2 | 348 Very Poor |
| Narela (DPCC) | 67 | 269 | 87.2 | 219 Poor |
| Bawana (DPCC) | 296 | 493 | 87.2 | 452 Severe |
| Wazirpur (DPCC) | 51 | 299 | 87.2 | 249 Poor |
| New Delhi (PM2.5 only) | 47 | - | 2.2 | 78 Satisfactory |
| Santushti Apts, Vasant Kunj (sensor) | 50.5 | - | 0.7 | 84 Satisfactory |
| Anand Lok (sensor) | 53.1 | - | 0.7 | 88 Satisfactory |
| GK1 Oberoi Terrace (sensor) | 62.5 | 238 | 0.7 | 192 Moderate |
| Air Check (sensor) | 59.2 | - | 0.7 | 99 Satisfactory |

**What this means**
1. The government readings are about **87 hours (3.6 days) old**. They show a very different (and much worse) picture than today's fresh sensors, so they must **not** be presented as current air quality or used for health advice.
2. A 3-hour freshness rule would currently reject every government station. The app needs a fallback, which the tiered strategy below provides.
3. The cause is unknown. It could be a temporary OpenAQ ingestion pause or an upstream outage. It may resolve on its own. Re-run the check on different days and times and keep notes: this is also good material for the blog ("what fought back").
4. The data shows a real story for the pitch: big differences between areas and between stale official readings and live sensors, which is exactly why showing **source and age** matters.
5. Cosmetic bug in the first version of the check script: a long PM10 value ran into the age column (GK1 row). Fixed in Appendix C (values are now rounded).

### 10.7 Tiered source strategy (final design)

For each area, `station_source.py` and the ingest Lambda choose the best available reading in this order:

| Tier | Source | Rule | Label shown in UI |
|---|---|---|---|
| 1 | Government station (DPCC/CPCB/IMD/IITM) | Reading age <= 3 hours and PM2.5 present; nearest within about 8 km | "Official station: Rohini (DPCC), 2 km away, updated 40 min ago" |
| 2 | Community/low-cost sensor | Age <= 2 hours, PM2.5 present, within about 5 km | "Community sensor (PM2.5 only, less accurate), 3 km away, updated 20 min ago" |
| 3 | OpenWeatherMap model | Always available | "Estimated from model data" |
| - | Stale government reading (older than 3 hours) | Never used for advice | Optional info line: "Last official reading was 3.6 days ago" |

Notes:
- Community sensors usually give PM2.5 only; AQI can be computed from PM2.5 alone but flag it. Low-cost optical sensors tend to read differently from reference-grade stations, so label them clearly (and keep them out of tier 1 claims).
- If the official feed returns, the app benefits automatically with no code change.
- Advice always uses the chosen tier's AQI and displays its source and age.
- Keep a **saved snapshot** of a "bad air day" (for example the 7 Oct official readings, clearly labelled as a recorded sample) for a reliable demo. Never present a stale reading as live.
- Cache by station, not by area, since several areas can share one station.

### 10.8 Station shortlist (from the 11 Oct 2026 run; verify again before relying)

Use the entry with recent data. Ignore duplicate IDs with 2018-2022 last-seen dates.

| Area | Station (OpenAQ id) | Notes |
|---|---|---|
| Anand Vihar | Anand Vihar, New Delhi - DPCC (235) | Full pollutant set |
| Rohini | Rohini, Delhi - DPCC (10831) | |
| R K Puram | R K Puram, Delhi - DPCC (17) | |
| Dwarka | Dwarka-Sector 8, Delhi - DPCC (6931); NSIT Dwarka - CPCB (5622) | |
| Central Delhi / ITO | ITO, New Delhi - CPCB (5613); Mandir Marg - DPCC (6358) | |
| Okhla | Okhla Phase-2, Delhi - DPCC (8239) | |
| Punjabi Bagh | Punjabi Bagh, Delhi - DPCC (50) | |
| Narela | Narela, Delhi - DPCC (10485) | |
| Bawana | Bawana, Delhi - DPCC (8472) | |
| Wazirpur | Wazirpur, Delhi - DPCC (8915) | |
| Ashok Vihar | Ashok Vihar, Delhi - DPCC (8917) | |
| Alipur | Alipur, Delhi - DPCC (6932) | |
| Mundka | Mundka, Delhi - DPCC (10486) | |
| Jahangirpuri | Jahangirpuri, Delhi - DPCC (8235) | |
| Vivek Vihar | Vivek Vihar, Delhi - DPCC (6938) | |
| Patparganj | Patparganj, Delhi - DPCC (6960) | |
| Nehru Nagar | Nehru Nagar, Delhi - DPCC (8365) | |
| Sonia Vihar | Sonia Vihar, Delhi - DPCC (8475) | |
| JNU / South Delhi | JNU, Delhi - DPCC (6254663); Sri Aurobindo Marg - DPCC (10484); IIT Delhi - IITM (6148686); Sirifort - CPCB (5586) | |
| Najafgarh | Najafgarh, Delhi - DPCC (10488) | |
| Shadipur | Shadipur, Delhi - CPCB (5630) | |
| Pusa | Pusa, Delhi - DPCC (6356) | |
| North Campus (DU) | North Campus, DU - IMD (5610) | |
| Lodhi Road | Lodhi Road, New Delhi - IMD (5634) | |
| Jawaharlal Nehru Stadium | JLN Stadium - DPCC (6957) | |
| DTU | DTU, New Delhi - CPCB (5626) | |
| Burari | Burari Crossing - IMD (5541) | |
| Chandni Chowk | Chandni Chowk - IITM (11603) | |
| Mathura Road | CRRI Mathura Road - IMD (5627) | |
| Vasant Kunj | Santushti Apartments sensor (4663956) | Community sensor, PM2.5 only |
| Anand Lok / South Ext. | Anand Lok sensor (6145551) | Community sensor |
| Greater Kailash | GK1 Oberoi Terrace sensor (2860223) | Community sensor, PM2.5 + PM10 |
| Central (fresh) | Air Check sensor (4712609); "New Delhi" PM2.5-only (8118) | Fresh today |

NCR stations (Noida, Gurugram, Ghaziabad, Faridabad) are also in the data; add them as a later expansion.

---

## 11. Step-by-step work plan

### Phase 0: Setup
- [ ] Verify student status on AWS Builder Center; confirm hackathon registration and team details.
- [ ] Create an AWS account (free tier). **Set a billing alarm/budget immediately.**
- [ ] Install Python 3.12, AWS CLI, **SAM CLI**, Git; run `aws configure`.
- [ ] Get an OpenWeatherMap key; confirm both current and **forecast** air pollution endpoints work.
- [ ] Get an OpenAQ key.
- [ ] Create a fresh GitHub repo; add `.gitignore` (`.env`, `.aws-sam/`, `__pycache__/`, `delhi_stations.json` optional). **Never commit keys.**

### Phase 1: Local engine
- [ ] Move `air_engine.py` into `backend/common/`; unit-test `sub_index` and `cpcb_aqi` (edge values at each breakpoint, missing pollutants).
- [ ] Add forecast fetch (`/air_pollution/forecast`) returning the next 24 hourly records.
- [ ] Expand `AREAS` to 12-20 localities and verify coordinates on a map.
- [ ] Update the CLI: choose area, choose profile, print pollutants, AQI, advice. Your original project stays alive as "local mode".
- **Done when:** the CLI prints correct, different readings for 5+ areas and advice changes with profile.

### Phase 2: Government station data
- [ ] Re-run `check_station_freshness.py` on different days/times and log how old the government data is.
- [ ] Optionally test the CPCB feed on data.gov.in as a second official source (access and terms unverified).
- [ ] Build the nearest-station mapping (haversine, precomputed), `station_source.py`, and the tiered selection from 10.7.
- [ ] Show source, distance and age in the UI for every reading.
- **Done when:** every area shows a reading with a visible source label, stale official data is never used for advice, and the fallback to tier 2/3 works.

### Phase 3: AWS backend
- [ ] Write `template.yaml` (SAM): DynamoDB tables, ingest Lambda + EventBridge schedule, api Lambda + HTTP API, SNS topic, SSM parameter references, least-privilege IAM.
- [ ] Implement `ingest` (loop areas, station-or-OWM, compute, batch write with TTL).
- [ ] Implement `api` with the four endpoints; add CORS for the frontend domain.
- [ ] Seed `Areas` (script or custom resource).
- [ ] `sam build && sam local invoke`; optionally LocalStack for DynamoDB/SNS.
- [ ] `sam deploy --guided`; trigger ingest manually; verify rows; curl the API URL.
- **Done when:** a public API URL returns live data and advice.

### Phase 4: Frontend
- [ ] Single page: area selector, profile selector, AQI card coloured by category (colour **and** text labels), pollutant bars, advice box, 24h outlook strip, "last updated" and source label, disclaimer.
- [ ] Mobile-first, large text; Hindi/English toggle (static strings first).
- [ ] Remember last area/profile in `localStorage`.
- [ ] Host on S3 + CloudFront (or Amplify Hosting); point at the API.
- **Done when:** a friend with no instructions can open the link on a phone and understand what to do.

### Phase 5: Alerts
- [ ] Subscribe form -> `/subscribe` -> store subscriber, send confirmation.
- [ ] Alert Lambda: after each ingest compare with `lastAlertCategory`, send profile-specific email via SNS.
- [ ] Unsubscribe path.
- [ ] SMS only if registration is workable; otherwise show a clearly labelled simulated SMS in the demo.

### Phase 6: Optional AI layer
- [ ] Bedrock (or Strands Agents SDK) rephrases/translates the approved advice. The rule table stays the source of truth. Cache outputs in DynamoDB.

### Phase 7: Stretch
- [ ] School mode (6:30 AM go/no-go, term summary of indoor-only days); Leaflet map; 24-48h trend chart.

### Phase 8: Hardening
- [ ] Test: invalid area, missing profile, API down, empty DB, stale data, station missing, duplicate subscription.
- [ ] CloudWatch alarms on Lambda errors; review logs.
- [ ] Review IAM; ensure no secrets in repo, logs, or frontend.
- [ ] Re-check costs after 24 hours of scheduled runs.

### Phase 9: Submission package
- [ ] README (problem, users, architecture diagram, setup, AWS services, limitations).
- [ ] 3-minute demo video.
- [ ] Blog post on AWS Builder Center; link it in the submission.
- [ ] Submit: repo, live URL, video, blog, track = Air.
- [ ] Request the extra $25 credits only after free credits are spent (team leader).

---

## 12. Demo video script and blog outline

### Demo (3 minutes)
| Time | Content |
|---|---|
| 0:00-0:25 | Problem: city-level AQI hides your neighbourhood and says nothing about what you should do |
| 0:25-1:10 | Live site: compare a polluted area with a cleaner one; show pollutant breakdown, dominant pollutant, and the source label (station vs estimate) |
| 1:10-1:50 | Switch profile from healthy adult to asthma/child; advice changes; show 24h outlook |
| 1:50-2:20 | Alert arrives (email, or clearly labelled simulated SMS) when an area worsens |
| 2:20-2:50 | Architecture slide: EventBridge, Lambda, DynamoDB, API Gateway, SNS, S3/CloudFront (SAM / Bedrock if used). Say where AWS fits |
| 2:50-3:00 | Impact and what's next (schools, more cities) |

Tips: clean screen resolution, clear narration, no aimless scrolling, subtitles. Keep a saved "bad air" sample dataset so the demo works even if today's air is clean.

### Blog outline (AWS Builder Center)
1. Why city-level AQI isn't enough
2. From a CLI script to a hosted service
3. Computing AQI from raw pollutants, and why we say "estimated"
4. Measured vs modelled data: adding government stations
5. Architecture and why serverless
6. What fought back (rate limits, stale/missing stations, SMS rules, CORS)
7. Costs and free tier
8. What's next

---

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| OWM values are modelled and may not match ground stations | Prefer station data; label "estimated"; show source |
| Station offline, stale, or far away | Freshness check, tiered fallback (10.7), show distance and age |
| Official feed stale for days (observed 11 Oct 2026: about 87 hours) | Tiered sources, honest labels, retry daily, saved labelled demo snapshot, mention in blog |
| Low-cost sensors less accurate than reference stations | Label as community sensors, PM2.5 only, never tier 1 |
| Health advice liability | Rule-based, precautionary, disclaimer, "follow your doctor's plan" |
| API key leakage | SSM SecureString; never in frontend; `.gitignore` |
| Unexpected AWS bill | Billing alarm, modest schedule, TTL on readings |
| SMS not workable in India | Email first; simulated SMS clearly labelled |
| Scope creep | Finish Phases 0-4 before anything else |
| Demo-day air is clean | Saved "bad day" sample mode |
| Judges can't use it | One screen, two dropdowns, plain language, phone-tested |
| Unverified assumptions (section 10.3) | Verify early; adjust plan |

---

## 14. Repo structure

```
saansalert/
  backend/
    common/        air_engine.py, advice.py, station_source.py, areas.json
    ingest/        app.py
    api/           app.py
    alerts/        app.py
    tests/
  scripts/         list_delhi_stations.py, check_station_freshness.py
  frontend/        index.html, app.js, styles.css, strings_en.json, strings_hi.json
  template.yaml    (SAM)
  README.md
  .gitignore
```

---

## 15. Status log, next actions, and how to run everything

### Done so far
- Idea selected and refined: area-level + health-profile air advice (SaansAlert).
- `air_engine.py` written (raw pollutants, CPCB-style AQI, 7 profiles x 4 tiers, area list, CLI). Not yet reported run by the user.
- OpenAQ key obtained; `list_delhi_stations.py` ran successfully (110 stations).
- `check_station_freshness.py` ran successfully and revealed that official station data is about 87 hours old (section 10.6).
- Tiered source strategy designed (10.7); station shortlist made (10.8).
- Plan, architecture, and this guide written.

### Next actions (in order)
1. Run `air_engine.py` and confirm different areas give different OpenWeatherMap readings and the advice changes with profile.
2. Re-run `check_station_freshness.py` later today and on another day; note the ages.
3. Verify the CPCB AQI breakpoints in `air_engine.py` against the official table; verify the area coordinates on a map.
4. Build `station_source.py` and the nearest-station mapping (use 10.7 and 10.8).
5. Optionally check the CPCB data.gov.in feed as a second official source.
6. Start Phase 3: SAM template + ingest and api Lambdas + DynamoDB.
7. Then frontend (Phase 4), alerts (Phase 5), hardening, demo video, blog, submission.
8. Set the AWS billing alarm as soon as the account exists.

### How to run the scripts
Folder layout (all in one folder for now):
```
saansalert/
  .env                       (never commit)
  air_engine.py
  list_delhi_stations.py
  check_station_freshness.py
```
`.env` contents:
```
OPENWEATHER_API_KEY=your_openweathermap_key
OPENAQ_API_KEY=your_openaq_key
```
Install: `pip install requests python-dotenv`

Run:
- `python air_engine.py` - pick an area and a health profile; uses OpenWeatherMap only.
- `python list_delhi_stations.py` - lists stations, saves `delhi_stations.json` (OpenAQ key).
- `python check_station_freshness.py` - latest PM values, age in hours, estimated AQI per shortlisted station (OpenAQ key; imports `air_engine.py`).

OpenAQ key: sign up at explore.openaq.org/register, **verify your email, log in**, open explore.openaq.org/account, and scroll to the **bottom** of the settings page. Treat keys like passwords.

### Open items (unverified or unknown)
- Why the official feed is stale, and when it resumes.
- OpenAQ rate limits and licence/attribution terms.
- The CPCB data.gov.in feed (access, terms, freshness).
- Whether SMS via SNS works in India for this project.
- Accuracy of the simplified AQI breakpoints and the approximate area coordinates.
- The accuracy of community sensors relative to reference stations.

---

## 16. Minimum viable checklist
1. Area picker + profile picker working locally
2. Pollutant-based AQI + advice correct
3. Deployed on AWS (Lambda + API Gateway + DynamoDB + S3/CloudFront)
4. Scheduled refresh running
5. 3-minute video + README + blog + submission

Everything else is a bonus.

---

## 17. Prompts to reuse with other AI assistants
- "Using this guide, write the SAM `template.yaml` for Phase 3 with least-privilege IAM."
- "Write the ingest Lambda in Python 3.12 using sections 9 and 10, with unit tests."
- "Write `station_source.py` implementing the tiered source strategy in section 10.7: for an area, pick the nearest fresh official station, else a fresh community sensor, else fall back; return components plus source, distance and age."
- "Write the nearest-station mapping script: read delhi_stations.json, drop stale/duplicate entries, and output an areas.json with stationId and distance."
- "Build the static frontend from section 4 of the plan, mobile-first, with a Hindi/English toggle."
- "Review the CPCB breakpoints in Appendix A against the official table and list differences."
- "Review Appendices B and C for bugs, rate-limit handling, and OpenAQ v3 edge cases."
- "Write the 3-minute demo narration from section 12 for my actual features."
- "Draft the Builder Center blog from section 12 using these notes: ..."

---

## Appendix A: air_engine.py

```python
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
```

## Appendix B: list_delhi_stations.py

```python
"""
list_delhi_stations.py - list OpenAQ monitoring stations around Delhi.

Setup:
  1. Get a free key at https://explore.openaq.org/register
  2. Add to your .env:  OPENAQ_API_KEY=your_key_here
  3. pip install requests python-dotenv
  4. python list_delhi_stations.py

Writes delhi_stations.json and prints a table. Send me the printed table
(or the JSON) so I can build the nearest-station lookup.
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("OPENAQ_API_KEY")
if not KEY:
    sys.exit("OPENAQ_API_KEY not found. Add it to your .env file.")

BASE = "https://api.openaq.org/v3/locations"
HEADERS = {"X-API-Key": KEY}

# Delhi centre. Radius is in metres; the API caps it (about 25 km), so we
# sweep a few centre points to cover Delhi-NCR.
CENTRES = {
    "Central Delhi": (28.6139, 77.2090),
    "North Delhi": (28.7300, 77.1200),
    "East Delhi": (28.6400, 77.3000),
    "South Delhi": (28.5300, 77.2000),
    "West Delhi": (28.6300, 77.0500),
}
RADIUS = 25000


def fetch(lat, lon):
    results, page = [], 1
    while True:
        params = {"coordinates": f"{lat},{lon}", "radius": RADIUS,
                  "limit": 100, "page": page}
        try:
            r = requests.get(BASE, headers=HEADERS, params=params, timeout=20)
        except requests.exceptions.RequestException as e:
            sys.exit(f"Network error: {e}")
        if r.status_code == 401:
            sys.exit("401 Unauthorized: check your API key.")
        if r.status_code == 429:
            sys.exit("429 Rate limited: wait a minute and retry.")
        if r.status_code != 200:
            sys.exit(f"API error {r.status_code}: {r.text[:300]}")
        batch = r.json().get("results", [])
        results.extend(batch)
        if len(batch) < 100:
            return results
        page += 1


def last_seen(loc):
    d = loc.get("datetimeLast")
    if isinstance(d, dict):
        return d.get("utc") or d.get("local") or "?"
    return d or "?"


def main():
    stations = {}
    for name, (lat, lon) in CENTRES.items():
        for loc in fetch(lat, lon):
            stations[loc["id"]] = loc

    rows = []
    for loc in stations.values():
        coords = loc.get("coordinates") or {}
        params = sorted({
            (s.get("parameter") or {}).get("name", "?")
            for s in loc.get("sensors", [])
        })
        provider = (loc.get("provider") or {}).get("name", "?")
        rows.append({
            "id": loc["id"],
            "name": loc.get("name"),
            "lat": coords.get("latitude"),
            "lon": coords.get("longitude"),
            "pollutants": params,
            "provider": provider,
            "last_seen_utc": last_seen(loc),
        })

    rows.sort(key=lambda x: str(x["name"]))
    with open("delhi_stations.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"\nFound {len(rows)} stations. Saved to delhi_stations.json\n")
    print(f"{'ID':<8}{'NAME':<38}{'LAT':<10}{'LON':<10}{'LAST SEEN (UTC)':<22}POLLUTANTS")
    print("-" * 110)
    for x in rows:
        lat = f"{x['lat']:.4f}" if x["lat"] is not None else "?"
        lon = f"{x['lon']:.4f}" if x["lon"] is not None else "?"
        print(f"{x['id']:<8}{str(x['name'])[:36]:<38}{lat:<10}{lon:<10}"
              f"{str(x['last_seen_utc'])[:20]:<22}{','.join(x['pollutants'])}")


if __name__ == "__main__":
    main()
```

## Appendix C: check_station_freshness.py

```python
"""
check_station_freshness.py - for a shortlist of OpenAQ stations, fetch the
LATEST PM2.5 / PM10 readings, show how old they are, and the estimated AQI.

Put it in the same folder as air_engine.py and your .env (needs OPENAQ_API_KEY).
Run:  python check_station_freshness.py
Then send me the printed table.
"""
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from air_engine import cpcb_aqi  # reuse the AQI calculation

load_dotenv()
KEY = os.getenv("OPENAQ_API_KEY")
if not KEY:
    sys.exit("OPENAQ_API_KEY not found in .env")

HEADERS = {"X-API-Key": KEY}
BASE = "https://api.openaq.org/v3/locations"

# id: label.  Government stations (most recent entries) + a few fresh
# low-cost / other sensors for comparison.
STATIONS = {
    235: "Anand Vihar (DPCC)",
    10831: "Rohini (DPCC)",
    17: "R K Puram (DPCC)",
    6931: "Dwarka Sector 8 (DPCC)",
    5613: "ITO (CPCB)",
    8239: "Okhla Phase-2 (DPCC)",
    50: "Punjabi Bagh (DPCC)",
    10485: "Narela (DPCC)",
    8472: "Bawana (DPCC)",
    8915: "Wazirpur (DPCC)",
    8118: "New Delhi (pm25 only)",
    4663956: "Santushti Apts, Vasant Kunj (sensor)",
    6145551: "Anand Lok (sensor)",
    2860223: "GK1 Oberoi Terrace (sensor)",
    4712609: "Air Check (sensor)",
}


def get(url):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
        except requests.exceptions.RequestException as e:
            print(f"  network error: {e}")
            return None
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code != 200:
            print(f"  API {r.status_code}: {r.text[:150]}")
            return None
        return r.json()
    return None


def parse_utc(dt):
    s = dt.get("utc") if isinstance(dt, dict) else dt
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def check(loc_id, label):
    meta = get(f"{BASE}/{loc_id}")
    time.sleep(1)
    latest = get(f"{BASE}/{loc_id}/latest")
    time.sleep(1)
    if not meta or not latest or not meta.get("results"):
        return {"id": loc_id, "label": label, "error": "no data"}

    # sensor id -> parameter name
    sensors = {}
    for s in meta["results"][0].get("sensors", []):
        p = s.get("parameter") or {}
        sensors[s["id"]] = p.get("name")

    vals, newest = {}, None
    for item in latest.get("results", []):
        name = sensors.get(item.get("sensorsId"))
        when = parse_utc(item.get("datetime"))
        if name in ("pm25", "pm10") and item.get("value") is not None:
            vals[name] = (item["value"], when)
        if when and (newest is None or when > newest):
            newest = when

    now = datetime.now(timezone.utc)
    age = (now - newest).total_seconds() / 3600 if newest else None

    aqi = None
    comp = {}
    if "pm25" in vals:
        comp["pm2_5"] = vals["pm25"][0]
    if "pm10" in vals:
        comp["pm10"] = vals["pm10"][0]
    if comp:
        aqi = cpcb_aqi(comp)
    return {"id": loc_id, "label": label, "pm25": vals.get("pm25", (None,))[0],
            "pm10": vals.get("pm10", (None,))[0], "age_h": age, "aqi": aqi}


def main():
    print(f"\nNow (UTC): {datetime.now(timezone.utc):%Y-%m-%d %H:%M}\n")
    print(f"{'ID':<9}{'STATION':<38}{'PM2.5':<9}{'PM10':<9}{'AGE (hours)':<13}ESTIMATED AQI")
    print("-" * 100)
    for loc_id, label in STATIONS.items():
        r = check(loc_id, label)
        if "error" in r:
            print(f"{loc_id:<9}{label:<38}{r['error']}")
            continue
        age = f"{r['age_h']:.1f}" if r["age_h"] is not None else "?"
        aqi = f"{r['aqi'][0]} ({r['aqi'][1]})" if r["aqi"] else "-"
        pm25 = round(r["pm25"], 1) if r["pm25"] is not None else "-"
        pm10 = round(r["pm10"], 1) if r["pm10"] is not None else "-"
        print(f"{loc_id:<9}{label:<38}{str(pm25):<9}{str(pm10):<9}{age:<13}{aqi}")


if __name__ == "__main__":
    main()
```
