## 1. Project Scaffolding

- [x] 1.1 Create project structure (`src/data/`, `src/eda/`, `src/ml/`, `src/ops/`, `src/api/`, `data/`, `output/`)
- [x] 1.2 Create `requirements.txt` (pandas, numpy, scikit-learn, xgboost, mlflow, prefect, fastapi, uvicorn, streamlit, plotly/matplotlib, pydantic, requests, kagglehub or similar)
- [x] 1.3 Write `README.md` with business understanding: problem statement, objective, stakeholders (satisfies Business Understanding requirement)

## 2. Data Ingestion

- [x] 2.0 Pre-ingestion setup: add `truststore` (Zscaler TLS fix) and `python-dotenv` (env config) to `requirements.txt`; create `.env` with service config; create `.gitignore` to exclude `.venv/`, `data/`, `output/`, `mlruns/`, `.env`
- [x] 2.1 Implement ingestion script that downloads the full Ames Housing dataset (Kaggle API, falling back to public CSV mirror if Kaggle credentials unavailable)
- [x] 2.2 Add a row-count assertion (>= 2,500 rows) that fails loudly if the wrong dataset variant loads
- [x] 2.3 Save raw dataset to `data/raw/ames_housing.csv`

## 3. Data Preprocessing

- [x] 3.1 Implement summary statistics generation (describe()) for numeric columns, saved to `output/`
- [x] 3.2 Implement missing-value report (count + percentage per column)
- [x] 3.3 Implement median imputation for numeric columns with missing values
- [x] 3.4 Implement categorical missing-value handling (e.g. fill with "None"/mode as appropriate per Ames Housing's documented semantics)
- [x] 3.5 Implement dtype reporting/logging for all columns
- [x] 3.6 Implement normalization (StandardScaler) of numeric features, saved as a separate scaled feature set for the linear model
- [x] 3.7 Save processed dataset to `data/processed/`

## 4. Exploratory Data Analysis

- [x] 4.1 Compute correlation matrix of numeric features vs. SalePrice, save top correlated features
- [x] 4.2 Analyze at least one categorical feature vs. SalePrice (group-by mean)
- [x] 4.3 Bin at least one continuous feature (e.g. house age from YearBuilt) into ranges, report counts per bin
- [x] 4.4 Encode categorical features (one-hot for nominal, ordinal encoding for quality-scale fields), produce fully numeric feature matrix
- [x] 4.5 Generate univariate plot (SalePrice distribution) and save as image artifact
- [x] 4.6 Generate bivariate plot (top feature vs. SalePrice scatter) and save as image artifact
- [x] 4.7 Generate correlation heatmap and save as image artifact

## 4b. Integration Verification (Groups 2–4)

- [x] 4b.1 Run ingest → preprocess → eda in sequence; verify zero nulls in encoded dataset and all output files present (found and fixed Fence ordinal map key mismatch: MnWw not MnWo)

## 5. DataOps: Scheduled Pipeline (Prefect)

- [x] 5.1 Wrap ingestion + preprocessing + EDA steps (2 and 3 and 4) as Prefect tasks within a single flow
- [x] 5.2 Add logging within each Prefect task (start/end time, row counts, key stats) visible in Prefect's run logs
- [x] 5.3 Create a Prefect deployment for this flow with a 2-minute interval schedule
- [x] 5.4 Verify locally: start a Prefect server, apply the deployment, confirm runs appear in the Prefect UI every ~2 minutes with logs

## 6. ML Pipeline: Training and Evaluation

- [x] 6.1 Implement 70/30 train/test split with a fixed random seed on the encoded feature matrix
- [x] 6.2 Train Ridge/Lasso regression on the normalized/scaled features
- [x] 6.3 Train XGBoost regression on the raw (unscaled) encoded features
- [x] 6.4 Compute RMSE, MAE, R², and MAPE for each model on the test set
- [x] 6.5 Produce a feature-importance ranking (coefficients for linear model, `feature_importances_` for XGBoost)
- [x] 6.6 Produce a side-by-side model comparison table/report

## 7. MLOps: MLflow Tracking

- [x] 7.1 Configure MLflow tracking URI (local SQLite backend)
- [x] 7.2 Log hyperparameters, all 4 metrics, and the model artifact for each of the two training runs to MLflow
- [x] 7.3 Register the better-performing model in the MLflow Model Registry (e.g. stage "Staging" or "Production")
- [x] 7.4 Verify locally: start MLflow UI, confirm both runs, metrics, and registered model are visible

## 8. API Layer (FastAPI)

- [x] 8.1 Define Pydantic request/response schemas for the prediction endpoint (house features in, predicted price + model version out)
- [x] 8.2 Implement `POST /predict` — loads the registered model from MLflow Model Registry, returns prediction
- [x] 8.3 Implement `GET /health` — checks MLflow and Prefect reachability, returns status
- [x] 8.4 Implement `GET /app-info/model` — wraps MLflow Model Registry API (name, version, stage)
- [x] 8.5 Implement `GET /app-info/experiment/{model_name}` — wraps MLflow Tracking API (experiment name, ID, run summary for the specified model)
- [x] 8.6 Implement `GET /app-info/pipeline/{deployment_name}` — wraps Prefect deployments API (deployment name, schedule, flow name)
- [x] 8.7 Implement `GET /app-info/runs/{deployment_name}` — wraps Prefect flow-runs API (recent run statuses/timestamps)
- [x] 8.8 Add graceful 503 handling when MLflow/Prefect are unreachable from any `/app-info/*` endpoint
- [x] 8.9 Verify `/docs` (Swagger UI) renders all endpoints correctly
- [x] 8.10 Add GET /app-info/eda/charts and GET /app-info/eda/summary endpoints to FastAPI (base64-encoded PNGs + summary stats JSON)

## 9. Dashboard (Streamlit)

- [x] 9.1 Build EDA view: summary stats, correlation heatmap, univariate/bivariate charts — sourced only via calls to the FastAPI backend (serve pre-generated EDA artifacts through a FastAPI endpoint if needed)
- [x] 9.2 Build prediction view: form for house feature inputs, calls `POST /predict`, displays result
- [x] 9.3 Build app-details view: calls all four `/app-info/*` endpoints, displays results
- [x] 9.4 Confirm no direct dataset/model/MLflow/Prefect access exists in the Streamlit code — API calls only

## 10. Containerization (Docker Compose)

- [x] 10.1 Write Dockerfile for the FastAPI service
- [x] 10.2 Write Dockerfile for the Streamlit dashboard (fixed: CMD array must be single line)
- [x] 10.3 Write `docker-compose.yml` wiring FastAPI, Streamlit, Prefect server, and MLflow server with a shared volume for data/artifacts, `depends_on`, and healthchecks
- [x] 10.4 Verify `docker compose up --build` brings up all 4 services and they can reach each other by service name

## 11. End-to-End Verification

- [x] 11.1 Run the full stack, confirm the Prefect scheduled flow executes and appears in its UI
- [x] 11.2 Confirm MLflow shows both training runs with all 4 metrics and a registered model
- [x] 11.3 Confirm FastAPI `/predict` returns sensible predictions for a few sample inputs
- [x] 11.4 Confirm all four `/app-info/*` endpoints return real (non-hardcoded) data
- [x] 11.5 Confirm Streamlit dashboard renders EDA, prediction, and app-details views correctly end-to-end
- [ ] 11.6 Capture screenshots of each verified view (manual, outside this change's scope)
