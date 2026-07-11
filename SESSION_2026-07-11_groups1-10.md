# Session Checkpoint — Groups 1-10 Complete
Date: 2026-07-11
Last commit: 8bf5c9e

## What is done

| Group | Tasks | Status |
|-------|-------|--------|
| 1 — Scaffolding | 1.1–1.3 | ✅ complete |
| 2 — Ingestion | 2.0–2.3 | ✅ complete |
| 3 — Preprocessing | 3.1–3.7 | ✅ complete |
| 4 — EDA | 4.1–4.7 + 4b.1 integration check | ✅ complete |
| 5 — DataOps (Prefect) | 5.1–5.4 | ✅ complete |
| 6 — ML Pipeline | 6.1–6.6 | ✅ complete |
| 7 — MLflow Tracking | 7.1–7.4 | ✅ complete |
| 8 — API Layer (FastAPI) | 8.1–8.10 | ✅ complete |
| 9 — Dashboard (Streamlit) | 9.1–9.4 | ✅ complete |
| 10 — Containerization | 10.1–10.4 | ✅ complete |

## Group 10 — what was built

| File | Content |
|------|---------|
| `Dockerfile.api` | FastAPI image (python:3.11-slim, uvicorn on :8000) |
| `Dockerfile.streamlit` | Streamlit image (python:3.11-slim, streamlit on :8501) |
| `docker-compose.yml` | 5 services: mlflow, prefect-server, prefect-worker, api, streamlit |

## docker-compose.yml — 5 services

| Service | Image | Port | Role |
|---------|-------|------|------|
| `mlflow` | ghcr.io/mlflow/mlflow:v3.14.0 | 5000 | Tracking server + model registry |
| `prefect-server` | prefecthq/prefect:3-latest | 4200 | Prefect control plane + UI |
| `prefect-worker` | api-prefect-worker (Dockerfile.api) | — | Serves the 2-min scheduled pipeline |
| `api` | api-api (Dockerfile.api) | 8000 | FastAPI prediction + app-info endpoints |
| `streamlit` | api-streamlit (Dockerfile.streamlit) | 8501 | Dashboard |

## Key design decisions (Group 10)

- **MLflow via HTTP**: `MLFLOW_TRACKING_URI=http://mlflow:5000` — FastAPI talks to MLflow server over HTTP, not direct SQLite
- **5 services not 4**: Prefect needs both server + worker as separate containers
- **Host bind mounts**: `./data`, `./mlruns`, `./output` — reuses existing trained models
- **mlruns double-mount**: api container mounts `./mlruns:/Users/dvksuman/API/mlruns` (original host path) because artifact URIs in the DB are absolute paths
- **Env vars for all peer URLs**: `MLFLOW_TRACKING_URI`, `PREFECT_API_URL`, `FASTAPI_URL` — all read from env with local defaults

## Verified working (Group 10)

```
docker compose ps        → all 5 containers healthy
GET /health              → {"mlflow":"ok","prefect":"ok","model":"loaded","overall":"healthy"}
POST /predict            → $92,145 for qual=7, area=1500
GET /app-info/model      → AmesPricePredictor v2 @production
Streamlit → API (inter-container) → reachable via http://api:8000
```

## How to start the stack

```bash
cd /Users/dvksuman/API
docker compose up --build    # first time
docker compose up            # subsequent times (images already built)
```

## UIs available when stack is running

| UI | URL |
|----|-----|
| Streamlit dashboard | http://localhost:8501 |
| FastAPI Swagger | http://localhost:8000/docs |
| MLflow UI | http://localhost:5000 |
| Prefect UI | http://localhost:4200 |

## Exact next step

**Group 11 — End-to-End Verification** (tasks 11.1–11.6)

1. Run `/opsx:explore` first (CLAUDE.md hard gate)
2. Stack must be running (`docker compose up`)
3. Tasks:
   - 11.1 Prefect scheduled flow executes and appears in UI
   - 11.2 MLflow shows both training runs + registered model
   - 11.3 `/predict` returns sensible predictions for multiple inputs
   - 11.4 All `/app-info/*` endpoints return real data
   - 11.5 Streamlit renders all 3 views correctly
   - 11.6 Screenshots (manual, for assignment report)

Start prompt for next session:
> "Read `SESSION_2026-07-11_groups1-10.md` and continue with Group 11. Run `/opsx:explore` first."
