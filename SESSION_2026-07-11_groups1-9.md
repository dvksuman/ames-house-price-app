# Session Checkpoint — Groups 1-9 Complete
Date: 2026-07-11
Last commit: 7b4528a

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

## Key output files

| File | Content |
|------|---------|
| `src/api/main.py` | FastAPI app — 8 endpoints including 2 new EDA endpoints |
| `src/dashboard/app.py` | Streamlit entry point + sidebar navigation |
| `src/dashboard/api_client.py` | All HTTP calls (single source of truth for API access) |
| `src/dashboard/pages/eda.py` | EDA view: stats table, correlation chart, 3 PNG charts |
| `src/dashboard/pages/prediction.py` | Prediction form (10 fields + defaults) → POST /predict |
| `src/dashboard/pages/app_details.py` | App details: health, model registry, metrics, pipeline, runs |
| `mlruns.db` | MLflow SQLite — AmesPricePredictor version 2 @production |
| `data/models/` | ridge.joblib, lasso.joblib, xgboost.joblib, scaler_ml.joblib |

## All API endpoints (verified working)

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/predict` | 213-feature input → dollar price via XGBoost |
| GET | `/health` | MLflow + Prefect + model status |
| GET | `/app-info/model` | Registered model info from MLflow |
| GET | `/app-info/experiment/{model_name}` | Run metrics for ridge/lasso/xgboost |
| GET | `/app-info/pipeline/{deployment_name}` | Prefect deployment info |
| GET | `/app-info/runs/{deployment_name}` | Recent Prefect flow run history |
| GET | `/app-info/eda/charts` | Pre-generated PNG charts (base64-encoded JSON) |
| GET | `/app-info/eda/summary` | Summary stats + top correlations (JSON) |
| GET | `/docs` | Swagger UI ✅ |

## How to start services

```bash
cd /Users/dvksuman/API

# Terminal 1 — Prefect server
PREFECT_API_URL=http://127.0.0.1:4200/api prefect server start --host 127.0.0.1 --port 4200

# Terminal 2 — Prefect serve (pipeline deployment)
PREFECT_API_URL=http://127.0.0.1:4200/api python -m src.ops.pipeline_flow

# Terminal 3 — FastAPI
.venv/bin/uvicorn src.api.main:app --port 8000

# Terminal 4 — Streamlit dashboard
.venv/bin/streamlit run src/dashboard/app.py --server.port 8501

# Optional — MLflow UI
.venv/bin/mlflow ui --backend-store-uri sqlite:///mlruns.db --port 5000
```

## Dashboard navigation
- **EDA tab**: Shows summary stats table, correlation bar chart, 3 pre-generated PNG charts
- **Predict Price tab**: 10-field form → calls POST /predict → displays predicted dollar price
- **App Details tab**: System health, MLflow model registry, experiment metrics table (all 3 models), Prefect deployment info, recent run history

## Key runtime names

| Thing | Name / value |
|---|---|
| MLflow experiment | `ames-housing-price-prediction` |
| Registered model | `AmesPricePredictor` |
| Production alias | `production` (version 2) |
| Prefect deployment | `ames-housing-2min` |
| FastAPI port | 8000 |
| Streamlit port | 8501 |

## Exact next step

**Group 10 — Containerization (Docker Compose)** (tasks 10.1–10.3)

1. Run `/opsx:explore` first (CLAUDE.md hard gate)
2. Key tasks:
   - 10.1 Dockerfile for FastAPI service
   - 10.2 Dockerfile for Streamlit dashboard
   - 10.3 docker-compose.yml — FastAPI + Streamlit + Prefect server + MLflow server, shared volume, depends_on, healthchecks

Start prompt for next session:
> "Read `SESSION_2026-07-11_groups1-9.md` and continue with Group 10. Run `/opsx:explore` first."
