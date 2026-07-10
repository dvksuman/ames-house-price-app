# os lets us check if folders exist and create them
import os

# logging lets us print timestamped messages to the terminal
import logging

# pandas reads and manipulates tabular data (CSV files become DataFrames)
import pandas as pd

# numpy provides math helpers — we use it to check for NaN values
import numpy as np

# StandardScaler transforms numeric columns so they all have mean=0 and std=1
from sklearn.preprocessing import StandardScaler

# joblib saves Python objects (like a fitted scaler) to disk so we can reload them later
import joblib

# configure() applies the Zscaler TLS fix and loads .env — call before any internet or config use
# read_processed_csv() reads processed CSVs without converting "None" strings back to NaN
from src.utils import configure, read_processed_csv
configure()

# Create a logger for this file so all messages are prefixed with the module name
logger = logging.getLogger(__name__)

# ── paths ────────────────────────────────────────────────────────────────────

# Where the raw downloaded file lives (written by ingest.py)
RAW_PATH = "data/raw/ames_housing.csv"

# Where we save the cleaned (but unscaled) dataset — used by XGBoost and EDA
PROCESSED_PATH = "data/processed/ames_housing_processed.csv"

# Where we save the scaled (normalized) dataset — used by Ridge/Lasso
SCALED_PATH = "data/processed/ames_housing_scaled.csv"

# Where we save the fitted StandardScaler object — needed at prediction time
SCALER_PATH = "data/processed/scaler.joblib"

# Where we save the summary statistics table (describe output)
SUMMARY_STATS_PATH = "output/summary_stats.csv"

# Where we save the missing-value report (count and percentage per column)
MISSING_REPORT_PATH = "output/missing_values.csv"

# ── column lists ──────────────────────────────────────────────────────────────

# These categorical columns have missing values that mean "this house has no such feature"
# Filling them with the mode would lie — e.g. saying 99.6% of houses have an Excellent pool
# We fill them with the literal string "None" to truthfully represent "feature absent"
SEMANTIC_NA_COLS = [
    "Alley",          # no alley access
    "Mas Vnr Type",   # no masonry veneer
    "Bsmt Qual",      # no basement
    "Bsmt Cond",      # no basement
    "Bsmt Exposure",  # no basement
    "BsmtFin Type 1", # no basement
    "BsmtFin Type 2", # no basement
    "Fireplace Qu",   # no fireplace
    "Garage Type",    # no garage
    "Garage Finish",  # no garage
    "Garage Qual",    # no garage
    "Garage Cond",    # no garage
    "Pool QC",        # no pool
    "Fence",          # no fence
    "Misc Feature",   # no miscellaneous feature
]

# These numeric and ID columns should NOT be scaled — they are identifiers or the target
# Scaling the target (SalePrice) or an ID column would make no sense
EXCLUDE_FROM_SCALING = ["Order", "PID", "SalePrice"]


# ── main function ─────────────────────────────────────────────────────────────

def preprocess() -> str:
    # This is the main function — cleans the raw data and saves two processed versions
    # Returns the path to the cleaned (unscaled) dataset

    # Make sure the output folders exist before we try to write files into them
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    # Load the raw CSV file into a pandas DataFrame (a table with rows and columns)
    df = pd.read_csv(RAW_PATH)
    logger.info("Loaded raw data: %d rows x %d cols", len(df), len(df.columns))

    # ── task 3.1: summary statistics ─────────────────────────────────────────
    # describe() computes count, mean, std, min, quartiles, max for every numeric column
    summary = df.describe()

    # Save the summary table as a CSV file in the output folder
    summary.to_csv(SUMMARY_STATS_PATH)
    logger.info("Saved summary stats → %s", SUMMARY_STATS_PATH)

    # ── task 3.2: missing value report ───────────────────────────────────────
    # Count how many values are missing in each column
    missing_count = df.isnull().sum()

    # Calculate what percentage of rows are missing for each column
    missing_pct = (missing_count / len(df) * 100).round(2)

    # Combine count and percentage into a single table
    missing_report = pd.DataFrame({
        "missing_count": missing_count,
        "missing_pct": missing_pct,
    })

    # Keep only columns that actually have at least one missing value
    missing_report = missing_report[missing_report["missing_count"] > 0]

    # Sort by most missing at the top so the worst columns are easy to find
    missing_report = missing_report.sort_values("missing_count", ascending=False)

    # Save the missing value report as a CSV file
    missing_report.to_csv(MISSING_REPORT_PATH)
    logger.info("Saved missing value report → %s (%d cols with gaps)", MISSING_REPORT_PATH, len(missing_report))

    # ── task 3.3: numeric imputation (median) ─────────────────────────────────
    # Find all columns that hold numbers
    num_cols = df.select_dtypes(include="number").columns.tolist()

    # For each numeric column that has missing values, fill gaps with the column's median
    # Median is more robust than mean because it isn't pulled by extreme house prices
    for col in num_cols:
        # Check if this column has any missing values before touching it
        if df[col].isnull().any():
            # Garage Yr Blt: missing means "no garage" — fill with 0, not the median year
            if col == "Garage Yr Blt":
                df[col] = df[col].fillna(0)
                logger.info("Imputed %s → 0 (no garage)", col)
            else:
                # Calculate the median of all non-missing values in this column
                median_val = df[col].median()
                # Replace every missing value in this column with the median
                df[col] = df[col].fillna(median_val)
                logger.info("Imputed %s → median %.2f", col, median_val)

    # ── task 3.4: categorical imputation ─────────────────────────────────────
    # Fill semantic-NA columns with "None" (means "house has no such feature")
    for col in SEMANTIC_NA_COLS:
        # Only process the column if it exists in the dataset (safety check)
        if col in df.columns:
            # Replace every missing value in this column with the string "None"
            df[col] = df[col].fillna("None")

    logger.info("Filled %d semantic-NA categorical columns with 'None'", len(SEMANTIC_NA_COLS))

    # Electrical: only 1 row missing — fill with the most common value (mode)
    if "Electrical" in df.columns and df["Electrical"].isnull().any():
        # mode() returns a Series; [0] gets the first (most common) value
        elec_mode = df["Electrical"].mode()[0]
        df["Electrical"] = df["Electrical"].fillna(elec_mode)
        logger.info("Imputed Electrical → mode '%s'", elec_mode)

    # ── task 3.5: dtype reporting ─────────────────────────────────────────────
    # Log the data type of every column so we can confirm the data looks right
    logger.info("Column dtypes:")
    for col, dtype in df.dtypes.items():
        # Print each column name and its data type (int64, float64, object, etc.)
        logger.info("  %-30s %s", col, dtype)

    # Confirm no numeric column still has missing values after imputation
    remaining_numeric_nulls = df.select_dtypes(include="number").isnull().sum().sum()
    logger.info("Remaining nulls in numeric columns after imputation: %d", remaining_numeric_nulls)

    # ── task 3.7: save cleaned unscaled dataset ───────────────────────────────
    # Save the cleaned (imputed, but not yet scaled) dataset
    # XGBoost will use this — tree models don't need normalization
    # EDA (Group 4) will also use this as its starting point
    df.to_csv(PROCESSED_PATH, index=False)
    logger.info("Saved processed (unscaled) dataset → %s", PROCESSED_PATH)

    # ── task 3.6: normalization (StandardScaler) ──────────────────────────────
    # StandardScaler transforms each numeric column so its mean becomes 0 and std becomes 1
    # This is required for Ridge/Lasso — without it, a column measured in square feet
    # (values ~1000) would dominate over a column measured in years (values ~2000)

    # Build the list of numeric columns to scale (exclude IDs and the target)
    scale_cols = [c for c in num_cols if c not in EXCLUDE_FROM_SCALING]

    # Create a StandardScaler object (not yet fitted — just the tool)
    scaler = StandardScaler()

    # Make a copy of the cleaned dataset so we don't overwrite it
    df_scaled = df.copy()

    # Fit the scaler on the numeric columns and transform them in one step
    # fit_transform() learns the mean and std, then applies the transformation
    df_scaled[scale_cols] = scaler.fit_transform(df[scale_cols])

    # Save the scaled dataset as a separate CSV
    df_scaled.to_csv(SCALED_PATH, index=False)
    logger.info("Saved scaled dataset → %s (%d columns scaled)", SCALED_PATH, len(scale_cols))

    # Save the fitted scaler to disk so we can reuse it at prediction time
    # Without this, we'd have to re-fit on the full dataset every time — which is wrong
    joblib.dump(scaler, SCALER_PATH)
    logger.info("Saved fitted scaler → %s", SCALER_PATH)

    # Return the path to the processed (unscaled) dataset
    return PROCESSED_PATH


# ── run directly ──────────────────────────────────────────────────────────────

# This block only runs when you execute: python -m src.data.preprocess
# It does NOT run when this file is imported by another module (e.g. the Prefect flow)
if __name__ == "__main__":
    # Set up logging to print timestamped messages to the terminal
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    # Run preprocessing and print a short summary when done
    path = preprocess()

    # Load the processed dataset using the shared reader (preserves "None" strings)
    df = read_processed_csv(path)
    print(f"\nPreprocessing complete.")
    print(f"Processed dataset: {path}")
    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} cols")
    print(f"Remaining nulls: {df.isnull().sum().sum()}")
    print(f"\nOutputs written:")
    print(f"  {SUMMARY_STATS_PATH}")
    print(f"  {MISSING_REPORT_PATH}")
    print(f"  {PROCESSED_PATH}")
    print(f"  {SCALED_PATH}")
    print(f"  {SCALER_PATH}")
