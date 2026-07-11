## Why

Building and demonstrating a cloud-native, API-driven data science/ML application end-to-end: a scheduled data pipeline, a machine learning pipeline with monitoring, and API-based access to application details. This proposal scopes the full build in one pass so implementation can start immediately.

## What Changes

- Ingest the Ames Housing dataset (~2,930 records) from a public source, with a documented business problem (house sale price prediction).
- Build a preprocessing + EDA pipeline: summary statistics, missing-value detection and imputation, dtype reporting, normalization, correlation analysis, binning, encoding, feature importance, univariate/bivariate visualizations.
- Automate preprocessing + EDA as a Prefect flow scheduled every 2 minutes, with run history/logs visible in Prefect's UI (serving as the "cloud dashboard" for DataOps activity).
- Train two contrasting regression models (Ridge/Lasso Linear Regression, XGBoost) on a 70/30 split, evaluate with regression metrics (RMSE, MAE, R², MAPE), and track all runs/metrics/models in MLflow (MLOps monitoring, ≥4 logged metrics, model registry).
- Serve predictions and expose ≥4 built-in application/deployment details (wrapping MLflow's and Prefect's own APIs) via a FastAPI service.
- Provide a Streamlit dashboard (calling the FastAPI backend only) to present EDA visuals, request predictions, and display the exposed API/app details.
- Containerize everything (FastAPI, Streamlit, Prefect server, MLflow server) via Docker Compose as a single local "cloud-native" stack.

## Capabilities

### New Capabilities
- `data-pipeline`: Ingestion, preprocessing, EDA, and a 2-minute-scheduled DataOps flow (Prefect) with logging and dashboard visibility for the Ames Housing dataset.
- `ml-pipeline`: Model training (Ridge/Lasso + XGBoost) on a 70/30 split, evaluation, and MLOps metric/run tracking via MLflow (≥4 metrics).
- `api-access`: FastAPI endpoints exposing ≥4 built-in application/deployment details sourced from MLflow's and Prefect's own APIs, plus a prediction endpoint.
- `prediction-dashboard`: Streamlit UI, API-driven, for EDA visuals, price prediction requests, and app-details display.

### Modified Capabilities
(none — greenfield project, no existing specs)

## Impact

- New repo at `/Users/dvksuman/API`: Python source tree, Dockerfile(s), `docker-compose.yml`, `requirements.txt`.
- External dependency: Ames Housing dataset download (Kaggle or public De Cock CSV mirror).
- New services: FastAPI (prediction + app-details API), Streamlit (dashboard), Prefect server (orchestration + UI), MLflow server (tracking + registry), all as Docker containers on the user's machine — no external cloud account required.
- Out of scope for this change: the Word report with screenshots and the demo video (manual deliverables produced after the app works).
