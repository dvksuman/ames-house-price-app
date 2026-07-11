# Session Checkpoint — Groups 1-8 Complete
Date: 2026-07-11
Last commit: 0b6e294

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
| 8 — API Layer (FastAPI) | 8.1–8.9 | ✅ complete |

## Key output files

| File | Content |
|------|---------|
| `src/api/main.py` | Full FastAPI app — all 6 endpoints |
| `src/ml/train_mlflow.py` | Fixed (no SalePrice leakage); re-ran, model v2 registered |
| `mlruns.db` | MLflow SQLite — AmesPricePredictor version 2 @production |
| `data/models/` | ridge.joblib, lasso.joblib, xgboost.joblib, scaler_ml.joblib |
| `output/model_comparison.json` | Side-by-side metrics for API use |

## API endpoints (all verified working)

| Method | Path | What it does |
|--------|------|--------------|
| POST | `/predict` | 213-feature input → dollar price via XGBoost |
| GET | `/health` | MLflow + Prefect + model status |
| GET | `/app-info/model` | Registered model info from MLflow |
| GET | `/app-info/experiment/{model_name}` | Run metrics for ridge/lasso/xgboost |
| GET | `/app-info/pipeline/{deployment_name}` | Prefect deployment info |
| GET | `/app-info/runs/{deployment_name}` | Recent Prefect flow run history |
| GET | `/docs` | Swagger UI ✅ |

## Model results (version 2 — no leakage)

| Model | R² | RMSE ($) | MAPE |
|-------|----|----------|------|
| Ridge | 0.852 | $34,008 | 8.48% |
| Lasso | 0.903 | $30,068 | 8.35% |
| XGBoost | **0.929** | **$23,407** | **7.62%** |

Note: version 1 had R²=0.994 due to SalePrice data leakage. Version 2 is the legitimate model.

## Key runtime names

| Thing | Name / value |
|---|---|
| MLflow experiment | `ames-housing-price-prediction` |
| Registered model | `AmesPricePredictor` |
| Production alias | `production` (version 2) |
| Prefect deployment | `ames-housing-2min` |
| Prefect flow | `ames-housing-pipeline` |

## How to start services

```bash
cd /Users/dvksuman/API

# Terminal 1 — Prefect server
PREFECT_API_URL=http://127.0.0.1:4200/api prefect server start --host 127.0.0.1 --port 4200

# Terminal 2 — Prefect serve (pipeline deployment)
PREFECT_API_URL=http://127.0.0.1:4200/api python -m src.ops.pipeline_flow

# Terminal 3 — FastAPI
.venv/bin/uvicorn src.api.main:app --port 8000

# Optional — MLflow UI
.venv/bin/mlflow ui --backend-store-uri sqlite:///mlruns.db --port 5000
```

## Exact next step

**Group 9 — Streamlit Dashboard** (tasks 9.1–9.3)

1. Run `/opsx:explore` first (CLAUDE.md hard gate)
2. Key tasks:
   - 9.1 EDA view: summary stats + charts, data sourced via FastAPI endpoints
   - 9.2 Prediction view: form → POST /predict → display result
   - 9.3 App-details view: calls all /app-info/* endpoints, displays results

Start prompt for next session:
> "Read `SESSION_2026-07-11_groups1-8.md` and continue with Group 9. Run `/opsx:explore` first."
