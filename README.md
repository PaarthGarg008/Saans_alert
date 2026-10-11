# SaansAlert

Area-level air quality and personalised health advice for Delhi-NCR, built on AWS.
*Not just how bad the air is, but what it means for you, where you live.*

**Track 01: Air.** Serverless on AWS: EventBridge, Lambda, DynamoDB, API Gateway (HTTP), SNS, S3 + CloudFront, SSM Parameter Store. Infrastructure is defined with **AWS SAM** (open source).

## What it does
- 20 Delhi localities, each matched to the nearest monitoring station.
- **Tiered data source, never stale:** fresh official station (≤3 h, ≤8 km) → fresh community sensor (≤2 h, ≤5 km) → OpenWeatherMap model estimate. Every reading shows its source, distance and age. A stale official reading is never used for advice.
- Estimated Indian (CPCB-style) AQI computed from raw PM2.5/PM10, with the dominant pollutant.
- Rule-based advice for 7 health profiles × 4 severity tiers, in English and Hindi (no AI-invented medical advice).
- 24-hour outlook (model), email alerts via SNS when an area worsens into Poor or beyond.
- Works offline in **demo mode** with a clearly labelled recorded sample (7 Oct 2026 official readings) for the demo video.

## Architecture
```
EventBridge (2 h) -> Lambda ingest -> OpenAQ (stations) / OpenWeatherMap (fallback + outlook)
                          |-> DynamoDB Readings (TTL 7 d), AlertState
                          '-> SNS topic per area -> email (filter policy: profile + language)
Browser -> CloudFront/S3 (static site) -> API Gateway HTTP API -> Lambda api -> DynamoDB / SNS
Keys: SSM Parameter Store SecureString.  Logs/alarms: CloudWatch.
```

## Repo layout
```
backend/common/   aqi.py, advice.py, selector.py (tier logic), sources.py, alerts.py, notify.py, areas.json
backend/ingest/   scheduled Lambda        backend/api/  HTTP API Lambda
backend/tests/    42 tests (AQI, tiers, alerts, API)
frontend/         index.html (single file), demo.js (recorded sample), config.js
scripts/          cli.py (local mode), make_demo_data.py, deploy_frontend.sh, seed_secrets.sh,
                  list_delhi_stations.py, check_station_freshness.py, air_engine.py (original scripts)
template.yaml     SAM template
docs/             SaansAlert_Final_Guide.md
```

## Run locally (no AWS)
```bash
pip install -r requirements-dev.txt
cp .env.example .env            # add OPENWEATHER_API_KEY and OPENAQ_API_KEY
cd backend && python -m pytest -q && cd ..
python scripts/cli.py --all asthma          # every area, with source labels
python scripts/cli.py rohini child
cd frontend && python -m http.server 8000   # demo mode at http://localhost:8000
```

## Deploy
1. AWS account, **billing budget/alarm first**, `aws configure`, install SAM CLI.
2. `scripts/seed_secrets.sh` (stores keys in SSM as SecureString).
3. `sam build && sam deploy --guided` (stack name `saansalert`).
4. Trigger the first ingest: `aws lambda invoke --function-name $(aws cloudformation describe-stacks --stack-name saansalert --query "Stacks[0].Outputs[?OutputKey=='IngestFunctionName'].OutputValue" --output text) /dev/stdout`
5. `scripts/deploy_frontend.sh` → prints the live URL.

## Design notes and known limitations
- **AQI is estimated:** official AQI uses 24 h averages; we use the latest reading. CPCB also wants ≥3 pollutants incl. one PM; we use PM2.5/PM10 only. Breakpoints match the published CPCB bands (PM2.5 30/60/90/120/250, PM10 50/100/250/350/430): confirm against the official table once more before final.
- **Official feed was ~87 h stale on 11 Oct 2026** (cause unknown); the tiering handles it, and the UI says so ("last official reading was X old, so it is not used"). Re-run `scripts/check_station_freshness.py` on other days and log the ages.
- Community sensors are PM2.5-only and read differently from reference stations: always labelled, never presented as official.
- Area coordinates and the area→station lists in `areas.json` are approximate; distances are computed at runtime from the station's own coordinates, and caps (8 km / 5 km) reject far stations.
- Email alerts use SNS: one topic per area, with a filter policy per subscriber. SNS allows one subscription per email per topic, so changing profile means unsubscribing (link in every email) and resubscribing. India SMS needs DLT registration; not used.
- Advice text is general precautionary guidance. Get it reviewed by a clinician before wide release.
- OpenAQ rate limits and attribution terms are unverified; ingest pauses 0.3 s between calls and caches per station. Add OpenAQ attribution in the footer before publishing.

## Status vs the guide
Done: Phase 1 (engine + tests + 20 areas), Phase 2 (station source + tiered selection), Phase 3 (SAM backend, written and unit-tested, **not yet deployed**), Phase 4 (frontend), Phase 5 (alerts, written, untested against real SNS). Next: deploy, verify on real data, 3-minute video, blog, submission.
