# Session Checkpoint — Groups 1-7 Complete
Date: 2026-07-11
Last commit: (see below — commit hook update + this file together)

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

## Key output files

| File | Shape / content |
|------|-----------------|
| `data/raw/ames_housing.csv` | 2930 rows × 82 cols |
| `data/processed/ames_housing_processed.csv` | 2930 rows, imputed, unscaled |
| `data/processed/ames_housing_scaled.csv` | 2930 rows, StandardScaler applied to numerics |
| `data/processed/scaler.joblib` | fitted StandardScaler (preprocessing) |
| `data/processed/ames_housing_encoded.csv` | 2930 × 215, fully numeric, 0 nulls, LogSalePrice target |
| `data/models/ridge.joblib` | trained Ridge model |
| `data/models/lasso.joblib` | trained Lasso model (zeroed 80/214 features) |
| `data/models/xgboost.joblib` | trained XGBoost model |
| `data/models/scaler_ml.joblib` | StandardScaler fitted on X_train (for API use) |
| `output/model_metrics.csv` | RMSE/MAE/R²/MAPE for all 3 models |
| `output/feature_importance.csv` | top 20 features per model |
| `output/model_comparison.csv` | side-by-side comparison table |
| `output/model_comparison.json` | same, JSON format (for FastAPI) |
| `output/plots/` | saleprice_dist.png, top_feature_scatter.png, correlation_heatmap.png |
| `src/ops/pipeline_flow.py` | Prefect flow (ingest→preprocess→eda), 2-min scheduled deployment |
| `src/ml/train.py` | Group 6 training script |
| `src/ml/train_mlflow.py` | Group 7 MLflow tracking script |
| `mlruns.db` | MLflow SQLite backend (experiment data) |
| `mlruns/` | MLflow artifact store (model files) |

## Model results (test set, 879 rows)

| Model | R² | RMSE ($) | MAPE |
|-------|----|----------|------|
| Ridge | 0.960 | $24,327 | 5.5% |
| Lasso | 0.962 | $25,828 | 5.3% |
| XGBoost | **0.994** | **$5,558** | **1.30%** |

**Best model: XGBoost** — registered in MLflow as `AmesPricePredictor@production`

## MLflow setup (local dev)

```bash
# Run tracking script (re-trains + logs all 3 models + registers XGBoost)
cd /Users/dvksuman/API
.venv/bin/python3 -m src.ml.train_mlflow

# Start MLflow UI
.venv/bin/mlflow ui --backend-store-uri sqlite:///mlruns.db --port 5000
# Open http://localhost:5000
```

## Prefect setup (local dev)

```bash
# Terminal 1 — server
cd /Users/dvksuman/API
PREFECT_API_URL=http://127.0.0.1:4200/api prefect server start --host 127.0.0.1 --port 4200

# Terminal 2 — serve (registers deployment + worker)
cd /Users/dvksuman/API
PREFECT_API_URL=http://127.0.0.1:4200/api python -m src.ops.pipeline_flow
```

## Python environment

Always use `.venv/bin/python3` (not system python3).

## Hooks

| Hook | File | Purpose |
|------|------|---------|
| Stop | `.claude/hooks/post_task_check.sh` | After every response: checks [~] tasks, doc freshness, uncommitted changes, SESSION file |
| PreToolUse | `.claude/hooks/pre_tool_gate.py` | Blocks writes to src/ unless a task is marked [~] in tasks.md |
| PostToolUse | `.claude/hooks/post_commit_check.py` | After Bash: checks SESSION file freshness after commits |

## Exact next step

**Group 8 — API Layer (FastAPI)** (tasks 8.1–8.9)

1. Run `/opsx:explore` first (CLAUDE.md hard gate)
2. Key tasks:
   - 8.1 Pydantic request/response schemas
   - 8.2 `POST /predict` — loads `AmesPricePredictor@production` from MLflow registry
   - 8.3 `GET /health` — checks MLflow + Prefect reachability
   - 8.4–8.7 `/app-info/*` endpoints wrapping MLflow + Prefect REST APIs
   - 8.8 Graceful 503 when services unreachable
   - 8.9 Verify `/docs` (Swagger UI)

**Model URI for FastAPI:** `models:/AmesPricePredictor@production`
**MLflow tracking URI:** `sqlite:////Users/dvksuman/API/mlruns.db`

Start prompt for next session:
> "Read `SESSION_2026-07-11_groups1-7.md` and continue with Group 8. Run `/opsx:explore` first."
