## Context

Greenfield project. Assignment requires a single cohesive app demonstrating a scheduled data pipeline, an ML pipeline with monitoring, and API-exposed application details — graded across three sub-objectives (8/5/2 marks). Solo build, due today, local machine only (no cloud account). A prior similar project (diabetes prediction, different repo) used FastAPI + Streamlit + Prefect + MLflow + Docker Compose successfully as an architecture pattern — reused here for a different domain/dataset, built fresh.

## Goals / Non-Goals

**Goals:**
- Satisfy every rubric activity literally (see proposal) with visible, screenshot-able evidence (Prefect UI runs, MLflow experiment/metrics, Swagger docs, Streamlit dashboard).
- Keep the stack simple enough to build and debug solo, same day.
- Make the "built-in APIs" sub-objective genuine — wrap real APIs (MLflow REST API, Prefect REST API) rather than inventing fake metadata endpoints.

**Non-Goals:**
- No deployment to a real cloud provider (AWS/GCP/Azure) — local Docker Compose only.
- No authentication/authorization, multi-tenancy, or CI/CD pipeline.
- No hyperparameter tuning sophistication beyond what's needed to show a working comparison between the two models.
- Report document and demo video are out of scope for this change (manual follow-up after the app works).

## Decisions

**Dataset: Ames Housing (full, ~2,930 rows), not the 1,460-row Kaggle-competition train split.**
Rationale: genuine, varied missing-value patterns (needed for the imputation rubric item) and rich mixed ordinal/nominal categoricals (needed for the encoding rubric item) that a cleaner/smaller dataset wouldn't provide. Source: download via `kagglehub`/Kaggle API if credentials available, else fall back to the public De Cock CSV mirror bundled as a pinned URL — ingestion code must verify row count ≈2900 after load and fail loudly if it silently got the 1460-row variant.

**Algorithms: Ridge/Lasso Linear Regression + XGBoost Regressor.**
Rationale: contrast interpretable/regularized linear model against a non-linear ensemble; motivates the normalization preprocessing step (matters for linear, irrelevant for XGBoost) rather than treating it as a checkbox.

**Orchestration: Prefect for the 2-minute DataOps schedule.**
Rationale: built-in web UI shows flow run history and logs out of the box, satisfying "log all activity + display on a dashboard" with minimal custom code. Prefect flow wraps preprocessing + EDA steps (not model training — training is a separate, manually/API-triggered flow, since retraining every 2 minutes on the same static dataset provides no signal and burns time).

**MLOps tracking: MLflow, local SQLite backend.**
Rationale: gives experiment tracking, ≥4 metrics per run, and a model registry for free, plus its own REST API — reusable for the "built-in APIs" sub-objective (`/api/2.0/mlflow/...`) instead of hand-rolling metadata storage.

**API layer: FastAPI.**
Rationale: auto-generated OpenAPI/Swagger docs at `/docs` double as report screenshot evidence; Pydantic validates prediction request/response schemas.

**Dashboard: Streamlit, calls FastAPI only (no direct DB/model access from the dashboard process).**
Rationale: keeps a clean API-driven architecture (the assignment's central theme) — the dashboard is a client of the API, not a second write path into the data/model layer.

**Deployment: Docker Compose, 4 services.**
```
┌──────────────────────────────────────────────────────────────┐
│                     docker-compose stack                      │
│                                                                 │
│  ┌────────────┐   ┌─────────────┐   ┌──────────────────────┐  │
│  │ Streamlit  │──▶│  FastAPI    │──▶│  MLflow client calls │  │
│  │  :8501     │   │  :8000      │   │  (model load, log)   │  │
│  └────────────┘   └──────┬──────┘   └──────────┬───────────┘  │
│                          │  wraps REST APIs of  │              │
│                          ▼                      ▼              │
│                  ┌───────────────┐     ┌────────────────┐     │
│                  │ Prefect server │     │ MLflow server  │     │
│                  │ :4200 (UI+API) │     │ :5000 (UI+API) │     │
│                  └───────────────┘     └────────────────┘     │
│                          ▲                                     │
│                  scheduled flow (every 2 min):                 │
│                  ingest → preprocess → EDA → log                │
└──────────────────────────────────────────────────────────────┘
```
Shared volume for the raw/processed dataset and EDA output artifacts (plots, logs) so Prefect's flow, the training script, and FastAPI can all read consistent files.

**Data flow for training (one-shot, not scheduled):** ingestion → preprocessing → train/test split (70/30) → train Ridge/Lasso + XGBoost → evaluate (RMSE/MAE/R²/MAPE) → log params+metrics+model to MLflow → register best model in MLflow Model Registry → FastAPI loads the registered model at startup (and via a `/reload` endpoint) for serving.

**"Built-in APIs" sub-objective implementation:** FastAPI endpoints that internally call MLflow's REST API and Prefect's REST API and reshape the response — e.g. `/app-info/model` (from MLflow registry API), `/app-info/experiment` (from MLflow experiment API), `/app-info/pipeline` (from Prefect deployments API), `/app-info/runs` (from Prefect flow-runs API). Satisfies "≥4 application/deployment details via built-in APIs" with real backing APIs, not mocked data.

## Risks / Trade-offs

- **[Risk] Kaggle API auth may not be set up on this machine, blocking dataset download.** → Mitigation: ingestion script tries Kaggle API first, falls back to a direct HTTPS download of the public Ames Housing CSV; document whichever path actually worked.
- **[Risk] Same-day deadline leaves little slack for Docker networking/debugging.** → Mitigation: get all 4 services running individually via plain `python`/`uvicorn`/`streamlit run` first, containerize last, once logic is proven.
- **[Risk] Prefect server + MLflow server both need to be up before FastAPI can wrap their APIs.** → Mitigation: `depends_on` + healthchecks in docker-compose; FastAPI's app-info endpoints handle connection errors gracefully (return 503 with a clear message) rather than crashing.
- **[Risk] XGBoost training time on 2,930 rows is trivial, but hyperparameter choices could still eat time if over-tuned.** → Mitigation: fixed, reasonable hyperparameters (no grid search) — this is a coursework demo, not a Kaggle leaderboard attempt.

## Open Questions

None blocking — proceed to specs/tasks. Resolve the Kaggle-vs-CSV-mirror ingestion path empirically during implementation and note the outcome in the code/comments.
