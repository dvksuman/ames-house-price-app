# Session Checkpoint — All Groups Complete
Date: 2026-07-11
Last commit: 31fd86f
OpenSpec: `build-house-price-app` archived as `2026-07-11-build-house-price-app`

## Status

All 11 task groups complete. OpenSpec change archived. Stack verified end-to-end.

| Group | Tasks | Status |
|-------|-------|--------|
| 1 — Scaffolding | 1.1–1.3 | ✅ complete |
| 2 — Ingestion | 2.0–2.3 | ✅ complete |
| 3 — Preprocessing | 3.1–3.7 | ✅ complete |
| 4 — EDA | 4.1–4.7 + 4b.1 | ✅ complete |
| 5 — DataOps (Prefect) | 5.1–5.4 | ✅ complete |
| 6 — ML Pipeline | 6.1–6.6 | ✅ complete |
| 7 — MLflow Tracking | 7.1–7.4 | ✅ complete |
| 8 — API Layer (FastAPI) | 8.1–8.10 | ✅ complete |
| 9 — Dashboard (Streamlit) | 9.1–9.4 | ✅ complete |
| 10 — Containerization | 10.1–10.4 | ✅ complete |
| 11 — End-to-End Verification | 11.1–11.5 ✅ / 11.6 manual | ✅ complete |

## Stack — verified working

| Service | Port | Status |
|---------|------|--------|
| MLflow | 5000 | healthy — 3 models registered, alias `production` on v2 |
| Prefect | 4200 | healthy — `ames-housing-2min` deployment running every 2 min |
| FastAPI | 8000 | healthy — all endpoints return real data |
| Streamlit | 8501 | healthy — all 3 views render correctly |

## Bugs fixed during Group 11

1. **`src/api/main.py`** — Prefect `flow_runs/filter` body keys: use `"deployments"` + `"flow_runs"` (not `*_filter` variants). Silent failure returned only SCHEDULED runs.
2. **`src/dashboard/pages/app_details.py`** — Experiment metrics keys: API returns `R2`, `RMSE_dollars`, `MAPE_pct`; dashboard was using lowercase variants. Also fixed schedule display from raw dict to human-readable "every 120 seconds (2 min)".

## Task 11.6 — remaining (manual)

Take screenshots of each verified view for the assignment report:
- http://localhost:8501 → EDA, Predict Price, App Details views
- http://localhost:5000 → MLflow runs + registered model
- http://localhost:4200 → Prefect deployment + run history

## How to start the stack

```bash
cd /Users/dvksuman/API
docker compose up
```

## OpenSpec archive location

```
openspec/archive/2026-07-11-build-house-price-app/
```
