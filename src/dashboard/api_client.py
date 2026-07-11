"""
api_client.py — the ONLY file in the dashboard that makes HTTP calls.
All other dashboard files import from here; none of them call requests directly.
This makes task 9.4 (API-only verification) trivial: just audit this one file.
"""

# Import the requests library for making HTTP calls.
import requests

# Read the FastAPI base URL from the environment — defaults to localhost for non-Docker use;
# inside Docker Compose this is set to http://api:8000.
import os
BASE_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")

# How long to wait for the API before giving up (in seconds).
TIMEOUT = 10


def get_eda_charts() -> dict:
    """Ask FastAPI for the pre-generated EDA chart images (base64-encoded PNGs)."""
    # Call the EDA charts endpoint and return the JSON response (dict of name → base64).
    resp = requests.get(f"{BASE_URL}/app-info/eda/charts", timeout=TIMEOUT)
    # Raise an error if the server returned a non-200 status code.
    resp.raise_for_status()
    return resp.json()


def get_eda_summary() -> dict:
    """Ask FastAPI for summary statistics and top correlations."""
    # Call the EDA summary endpoint.
    resp = requests.get(f"{BASE_URL}/app-info/eda/summary", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def predict(features: dict) -> dict:
    """Send a dict of house features to the prediction endpoint; return the result."""
    # POST the feature dictionary as JSON to /predict.
    resp = requests.post(f"{BASE_URL}/predict", json=features, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_health() -> dict:
    """Check the health of all backend services (model, MLflow, Prefect)."""
    resp = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_model_info() -> dict:
    """Get the registered model info from the MLflow Model Registry."""
    resp = requests.get(f"{BASE_URL}/app-info/model", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_experiment_info(model_name: str) -> dict:
    """Get MLflow run metrics for a given model (ridge / lasso / xgboost)."""
    resp = requests.get(f"{BASE_URL}/app-info/experiment/{model_name}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_pipeline_info(deployment_name: str) -> dict:
    """Get Prefect deployment details for the named deployment."""
    resp = requests.get(f"{BASE_URL}/app-info/pipeline/{deployment_name}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_run_history(deployment_name: str) -> dict:
    """Get recent Prefect flow run history for the named deployment."""
    resp = requests.get(f"{BASE_URL}/app-info/runs/{deployment_name}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
