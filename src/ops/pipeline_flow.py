# os lets us change the working directory so relative paths in the scripts resolve correctly
import os

# Path helps us find the project root regardless of where the process was started
from pathlib import Path

# pandas reads CSV files so we can report row counts in the task logs
import pandas as pd

# flow, task, get_run_logger are the three core Prefect building blocks we use
from prefect import flow, task, get_run_logger

# timedelta defines the interval duration (e.g. 2 minutes)
from datetime import timedelta

# Make sure all relative paths (data/raw, data/processed, output/) resolve from the project root
# This is needed because Prefect may start the process from a different directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.chdir(PROJECT_ROOT)


# ── task 5.1 + 5.2: ingest ────────────────────────────────────────────────────

@task(name="ingest", retries=1)
def ingest_task():
    # get_run_logger() returns a logger that sends messages to the Prefect UI
    log = get_run_logger()

    # Log that the task is starting so the UI shows a clear start marker
    log.info("▶  ingest starting  (project root: %s)", PROJECT_ROOT)

    # Import and call the ingest function from the existing ingest module
    from src.data.ingest import ingest
    path = ingest()

    # Read the saved file to report its shape in the Prefect logs
    df = pd.read_csv(path)

    # Log a completion summary: rows, columns, and where the file was saved
    log.info("✓  ingest done — %d rows × %d cols → %s", len(df), len(df.columns), path)

    # Return the path so the next task knows where to find the raw data
    return path


# ── task 5.1 + 5.2: preprocess ───────────────────────────────────────────────

@task(name="preprocess")
def preprocess_task(raw_path: str):
    # get_run_logger() gives us a Prefect-aware logger for this task
    log = get_run_logger()

    # Log that preprocessing is starting and which file we are about to process
    log.info("▶  preprocess starting  (input: %s)", raw_path)

    # Import and call the preprocessing function from the existing module
    from src.data.preprocess import preprocess
    path = preprocess()

    # Load the processed file to report its shape
    df = pd.read_csv(path)

    # Log a summary: how many rows and columns remain after cleaning
    log.info("✓  preprocess done — %d rows × %d cols → %s", len(df), len(df.columns), path)

    # Return the path to the cleaned dataset for the EDA task
    return path


# ── task 5.1 + 5.2: eda ──────────────────────────────────────────────────────

@task(name="eda")
def eda_task(processed_path: str):
    # get_run_logger() gives us a Prefect-aware logger for this task
    log = get_run_logger()

    # Log that EDA is starting and which file it will read
    log.info("▶  eda starting  (input: %s)", processed_path)

    # Import and call the EDA function from the existing module
    from src.eda.eda import run_eda
    path = run_eda()

    # Load the encoded dataset to report its final shape
    df = pd.read_csv(path)

    # Log a summary: number of rows and columns in the fully encoded feature matrix
    log.info("✓  eda done — %d rows × %d cols → %s", len(df), len(df.columns), path)

    # Return the path to the encoded dataset (useful for downstream tasks in later groups)
    return path


# ── task 5.1 + 5.2: flow ─────────────────────────────────────────────────────

@flow(name="ames-housing-pipeline", log_prints=True)
def pipeline():
    # get_run_logger() at the flow level logs to the same Prefect UI run view
    log = get_run_logger()

    # Log that the full pipeline is starting
    log.info("═══ Ames Housing Pipeline — run started ═══")

    # Step 1: download / validate the raw dataset
    raw_path = ingest_task()

    # Step 2: clean, impute, scale — reads raw, writes processed + scaled
    processed_path = preprocess_task(raw_path)

    # Step 3: EDA, encoding, plots — reads processed, writes encoded + charts
    encoded_path = eda_task(processed_path)

    # Log a final summary so the run view shows the end-to-end result at a glance
    log.info("═══ Pipeline complete — encoded dataset: %s ═══", encoded_path)

    # Return the encoded path so callers (e.g. a downstream ML flow) can pick it up
    return encoded_path


# ── task 5.3: deployment with 2-minute schedule ───────────────────────────────

# This block runs when you execute:  python -m src.ops.pipeline_flow
# It registers the deployment with the local Prefect server AND acts as the worker
if __name__ == "__main__":
    # serve() blocks indefinitely: it schedules and executes runs every 2 minutes
    # interval=timedelta(minutes=2) means "start a new run every 2 minutes"
    # name= is the deployment label shown in the Prefect UI
    pipeline.serve(
        name="ames-housing-2min",
        interval=timedelta(minutes=2),
    )
