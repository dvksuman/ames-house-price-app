# House Price Prediction — API-Driven Cloud-Native App

## Business Understanding

**Problem statement:** Estimating a house's sale price accurately, from its physical
and locational characteristics, is a recurring and high-stakes decision problem in
residential real estate — mispricing a listing either leaves money on the table or
causes it to sit unsold.

**Objective:** Build a regression model that predicts a house's `SalePrice` from its
features (lot size, quality ratings, square footage, neighborhood, etc.), and expose
that model as a monitored, API-accessible service rather than a one-off notebook.

**Stakeholders:**
- **Home sellers / real estate agents** — need a data-driven starting point for listing price, instead of relying purely on manual comparables.
- **Mortgage lenders / appraisers** — benefit from an independent, consistent price estimate to sanity-check appraisals and reduce over-lending risk.
- **Home buyers** — can use a predicted price to judge whether an asking price is reasonable relative to the house's actual characteristics.

## Dataset

Ames Housing dataset (full, ~2,930 records, ~80 features), sourced via Kaggle
(falls back to a public CSV mirror if Kaggle credentials aren't configured).

## Architecture

Five Docker Compose services wired together:

| Service | Port | Role |
|---------|------|------|
| `mlflow` | 5000 | Experiment tracking + model registry |
| `prefect-server` | 4200 | Pipeline scheduler + UI |
| `prefect-worker` | — | Runs the 2-minute scheduled pipeline |
| `api` | 8000 | FastAPI — prediction + app-info endpoints |
| `streamlit` | 8501 | Dashboard (API calls only, no direct DB access) |

```
Streamlit (8501)
     │  HTTP
     ▼
FastAPI (8000)
     │            │
     ▼            ▼
MLflow (5000)  Prefect (4200)
```

## Models

Three models trained on the Ames Housing dataset (70/30 split):

| Model | R² | RMSE ($) | MAPE (%) |
|-------|----|----------|----------|
| Ridge Regression | 0.8523 | 34,008 | 8.48% |
| Lasso Regression | 0.9026 | 30,068 | 8.35% |
| XGBoost | 0.9285 | 23,407 | 7.62% |

Best model (XGBoost) registered in MLflow Model Registry with alias `production`.

## Quick Start

**Prerequisites:** Docker Desktop running.

```bash
# Clone and start
git clone https://github.com/dvksuman/ames-house-price-app.git
cd ames-house-price-app
docker compose up
```

All 5 services start automatically. Wait ~30 seconds for health checks to pass.

| UI | URL |
|----|-----|
| Streamlit Dashboard | http://localhost:8501 |
| FastAPI Swagger Docs | http://localhost:8000/docs |
| MLflow UI | http://localhost:5000 |
| Prefect UI | http://localhost:4200 |

To stop:
```bash
docker compose down
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/predict` | Predict house price from features |
| `GET` | `/health` | MLflow + Prefect reachability check |
| `GET` | `/app-info/model` | Registered model info (MLflow) |
| `GET` | `/app-info/experiment/{model_name}` | Run metrics for ridge/lasso/xgboost |
| `GET` | `/app-info/pipeline/{deployment_name}` | Prefect deployment info |
| `GET` | `/app-info/runs/{deployment_name}` | Recent pipeline run history |
| `GET` | `/app-info/eda/charts` | EDA charts as base64 PNGs |
| `GET` | `/app-info/eda/summary` | Summary statistics JSON |

Example prediction:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"OverallQual": 7, "GrLivArea": 1500, "GarageCars": 2, "TotalBsmtSF": 800, "FullBath": 2, "YearBuilt": 2000}'
```

## Project Structure

```
src/
  data/         # Ingestion scripts
  eda/          # EDA + chart generation
  ml/           # Model training (Ridge, Lasso, XGBoost)
  ops/          # Prefect pipeline
  api/          # FastAPI app
  dashboard/    # Streamlit app
data/           # Raw + processed datasets (gitignored)
mlruns/         # MLflow tracking (gitignored)
output/         # EDA artifacts (gitignored)
Dockerfile.api
Dockerfile.streamlit
docker-compose.yml
```

## Pipeline

A Prefect flow runs every 2 minutes (configurable), executing the full
ingest → preprocess → EDA chain and logging results. Visible in the Prefect UI
at http://localhost:4200.
