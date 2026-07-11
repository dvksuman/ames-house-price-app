"""
Task 9.3 — App Details View
Displays live application state from all four /app-info/* endpoints.
All data comes from the FastAPI backend — no direct MLflow or Prefect access.
"""

# Import Streamlit for building the web UI.
import streamlit as st

# Import our API client — all HTTP calls go through here.
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.api_client import (
    get_health,
    get_model_info,
    get_experiment_info,
    get_pipeline_info,
    get_run_history,
)

# The known deployment name — used for the Prefect endpoints.
DEPLOYMENT_NAME = "ames-housing-2min"


def show():
    """Render the application details page."""

    # Page title.
    st.title("Application Details")
    st.markdown("Live status of all backend services — model registry, experiment tracking, and pipeline.")

    # ---- SECTION 1: HEALTH CHECK ----
    st.header("1. System Health")

    # Try to fetch the health status from the API.
    try:
        health = get_health()

        # Use colour-coded metric tiles to show status at a glance.
        col1, col2, col3, col4 = st.columns(4)

        # Overall status — green if healthy, red if degraded.
        overall = health.get("overall", "unknown")
        col1.metric("Overall", overall.upper())

        # Model load status.
        col2.metric("ML Model", health.get("model", "unknown").upper())

        # MLflow status.
        col3.metric("MLflow", health.get("mlflow", "unknown").upper())

        # Prefect status.
        col4.metric("Prefect", health.get("prefect", "unknown").upper())

        # Show the raw JSON in an expander for technical users.
        with st.expander("Raw health response"):
            st.json(health)

    except Exception as e:
        st.error(f"Could not reach health endpoint: {e}")

    st.divider()

    # ---- SECTION 2: MODEL REGISTRY INFO ----
    st.header("2. Registered Model (MLflow)")

    # Try to fetch model registry details.
    try:
        model_info = get_model_info()

        # Display key model fields in a two-column layout.
        col1, col2 = st.columns(2)
        col1.metric("Model Name", model_info.get("name", "—"))
        col2.metric("Version", model_info.get("version", "—"))
        col1.metric("Alias", model_info.get("alias", "—"))
        col2.metric("Run ID", model_info.get("run_id", "—")[:8] + "...")

        # Show description if present.
        desc = model_info.get("description", "")
        if desc:
            st.caption(f"Description: {desc}")

        with st.expander("Raw model registry response"):
            st.json(model_info)

    except Exception as e:
        st.error(f"Could not load model info: {e}")

    st.divider()

    # ---- SECTION 3: EXPERIMENT METRICS ----
    st.header("3. Experiment Metrics (MLflow)")

    # Fetch and compare metrics for all three model types.
    model_names = ["ridge", "lasso", "xgboost"]

    # Build a table of metrics across the three models.
    import pandas as pd
    rows = []

    for model_name in model_names:
        try:
            # Call the experiment endpoint for each model type.
            exp_info = get_experiment_info(model_name)
            metrics = exp_info.get("metrics", {})

            # Build a row with the key metrics we care about.
            rows.append({
                "Model": model_name.capitalize(),
                "R²": round(metrics.get("R2", 0), 4),
                "RMSE ($)": round(metrics.get("RMSE_dollars", 0), 0),
                "MAPE (%)": round(metrics.get("MAPE_pct", 0), 2),
            })
        except Exception as e:
            # If a model's metrics can't be fetched, show a dash row.
            rows.append({"Model": model_name.capitalize(), "R²": "—", "RMSE ($)": "—", "MAPE": f"error: {e}"})

    # Display the metrics as a dataframe table.
    if rows:
        metrics_df = pd.DataFrame(rows).set_index("Model")
        st.dataframe(metrics_df, use_container_width=True)

    st.divider()

    # ---- SECTION 4: PIPELINE / DEPLOYMENT INFO ----
    st.header("4. Pipeline Deployment (Prefect)")

    # Fetch Prefect deployment details.
    try:
        pipeline_info = get_pipeline_info(DEPLOYMENT_NAME)

        # Show the key deployment fields.
        col1, col2 = st.columns(2)
        col1.metric("Deployment Name", pipeline_info.get("deployment_name", "—"))
        col2.metric("Flow Name", pipeline_info.get("flow_name", "—"))
        col1.metric("Status", str(pipeline_info.get("status", "—")))

        # Show the schedule interval in a human-readable form.
        schedules = pipeline_info.get("schedule")
        if schedules and isinstance(schedules, list) and schedules:
            interval_sec = schedules[0].get("schedule", {}).get("interval")
            if interval_sec:
                st.caption(f"Schedule: every {int(interval_sec)} seconds ({int(interval_sec)//60} min)")

        with st.expander("Raw pipeline response"):
            st.json(pipeline_info)

    except Exception as e:
        st.error(f"Could not load pipeline info: {e}")

    st.divider()

    # ---- SECTION 5: RECENT RUN HISTORY ----
    st.header("5. Recent Pipeline Runs (Prefect)")

    # Fetch the last 10 flow run records.
    try:
        run_data = get_run_history(DEPLOYMENT_NAME)
        recent_runs = run_data.get("recent_runs", [])

        if recent_runs:
            # Convert to a DataFrame for a clean table display.
            runs_df = pd.DataFrame(recent_runs)

            # Rename columns to be more readable.
            runs_df = runs_df.rename(columns={
                "run_id": "Run ID",
                "name": "Run Name",
                "state": "State",
                "start_time": "Start Time",
                "end_time": "End Time",
                "total_run_time": "Duration (s)",
            })

            # Show just a short prefix of the run ID to save space.
            if "Run ID" in runs_df.columns:
                runs_df["Run ID"] = runs_df["Run ID"].astype(str).str[:8]

            st.dataframe(runs_df, use_container_width=True)
        else:
            st.info("No recent runs found. The pipeline may not have been triggered yet.")

    except Exception as e:
        st.error(f"Could not load run history: {e}")
