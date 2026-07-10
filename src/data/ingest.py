# os lets us check if files/folders exist and create folders
import os

# glob finds files matching a pattern — used to search inside Kaggle's download folder
import glob

# logging lets us print timestamped messages instead of bare print() calls
import logging

# StringIO lets us treat a text string as if it were a file — used for the fallback URL
from io import StringIO

# configure() applies the Zscaler TLS fix and loads .env — must run before any internet call
from src.utils import configure
configure()

# requests downloads files from the internet over HTTP/HTTPS
import requests

# pandas reads CSV files into a table (called a DataFrame) that we can query and manipulate
import pandas as pd

# kagglehub is Kaggle's official Python library for downloading datasets
import kagglehub

# Create a logger for this file — messages will appear with the module name as a prefix
logger = logging.getLogger(__name__)

# Folder where we store the raw downloaded file
RAW_DIR = "data/raw"

# Full path to the file we will save
OUTPUT_PATH = os.path.join(RAW_DIR, "ames_housing.csv")

# The Kaggle dataset identifier — "owner/dataset-name" format
# marcopale/housing was verified to contain the full 2,930-row dataset
KAGGLE_DATASET = "marcopale/housing"

# The specific CSV file inside the Kaggle dataset we want
KAGGLE_FILE = "AmesHousing.csv"

# Public URL for the original dataset published by Dean De Cock (the dataset's author)
# Used as a backup if Kaggle is unavailable
FALLBACK_URL = "https://jse.amstat.org/v19n3/decock/AmesHousing.txt"

# Minimum number of rows we accept — anything less means we got the wrong dataset variant
MIN_ROWS = 2500


def ingest() -> str:
    # This is the main function — it downloads the dataset and returns the path to the saved file

    # Create the data/raw/ folder if it doesn't already exist
    # exist_ok=True means "don't error if the folder is already there"
    os.makedirs(RAW_DIR, exist_ok=True)

    # IDEMPOTENCY CHECK: if a valid file already exists, skip the download
    # This prevents re-downloading on every Prefect run (which fires every 2 minutes)
    if os.path.exists(OUTPUT_PATH):
        # Load the existing file into a DataFrame to check its row count
        existing = pd.read_csv(OUTPUT_PATH)

        if len(existing) >= MIN_ROWS:
            # File is valid — log a message and return its path without downloading again
            logger.info("Using cached file: %s (%d rows)", OUTPUT_PATH, len(existing))
            return OUTPUT_PATH

        # File exists but has too few rows — warn and fall through to re-download
        logger.warning("Cached file has only %d rows — re-downloading", len(existing))

    # PRIMARY SOURCE: try Kaggle first
    df = _try_kaggle()

    # FALLBACK SOURCE: if Kaggle failed (no credentials, network issue, etc.), try the public URL
    if df is None:
        df = _try_fallback()

    # If both sources failed, stop with a clear error message
    if df is None:
        raise RuntimeError(
            "All data sources failed. "
            "Check internet connectivity and Kaggle credentials (~/.kaggle/kaggle.json)."
        )

    # ROW COUNT ASSERTION: fail loudly if we got fewer rows than expected
    # This catches the case where we accidentally downloaded the 1,460-row competition split
    if len(df) < MIN_ROWS:
        raise ValueError(
            f"Dataset has only {len(df)} rows (expected >= {MIN_ROWS}). "
            "This is likely the 1,460-row Kaggle competition split, not the full dataset. "
            "Use Kaggle dataset 'marcopale/housing' or the jse.amstat.org URL."
        )

    # Save the DataFrame as a CSV file to data/raw/ames_housing.csv
    # index=False means don't write the row numbers (0, 1, 2...) as a column
    df.to_csv(OUTPUT_PATH, index=False)

    # Log how many rows and columns were saved
    logger.info("Saved %d rows x %d cols to %s", len(df), len(df.columns), OUTPUT_PATH)

    # Return the path so the caller knows where the file landed
    return OUTPUT_PATH


def _try_kaggle() -> pd.DataFrame | None:
    # Try to download from Kaggle — returns a DataFrame on success, None on any failure
    try:
        logger.info("Trying Kaggle dataset: %s", KAGGLE_DATASET)

        # kagglehub downloads the dataset to its own hidden cache folder (~/.cache/kagglehub/...)
        # and returns the path to that folder
        cache_path = kagglehub.dataset_download(KAGGLE_DATASET)

        # Search for AmesHousing.csv specifically inside the downloaded folder
        candidates = glob.glob(f"{cache_path}/**/{KAGGLE_FILE}", recursive=True)

        # If the specific file wasn't found, look for any CSV file in the folder
        if not candidates:
            candidates = glob.glob(f"{cache_path}/**/*.csv", recursive=True)

        # If no CSV was found at all, warn and return None to trigger the fallback
        if not candidates:
            logger.warning("No CSV found in Kaggle cache at %s", cache_path)
            return None

        # Read the first matching CSV into a pandas DataFrame
        df = pd.read_csv(candidates[0])

        logger.info("Kaggle OK: %d rows from %s", len(df), candidates[0])
        return df

    except Exception as exc:
        # Something went wrong (no credentials, network error, etc.) — log and return None
        logger.warning("Kaggle download failed: %s", exc)
        return None


def _try_fallback() -> pd.DataFrame | None:
    # Try to download from the public jse.amstat.org URL — returns a DataFrame or None
    try:
        logger.info("Trying fallback URL: %s", FALLBACK_URL)

        # Download the file content — timeout=30 means give up after 30 seconds
        response = requests.get(FALLBACK_URL, timeout=30)

        # raise_for_status() throws an error if the server returned a failure code (4xx, 5xx)
        response.raise_for_status()

        # The jse.amstat.org file is tab-separated (not comma-separated)
        # StringIO wraps the text so pandas can read it as if it were a file
        df = pd.read_csv(StringIO(response.text), sep="\t")

        logger.info("Fallback OK: %d rows", len(df))
        return df

    except Exception as exc:
        # Network error, server down, TLS issue, etc. — log and return None
        logger.warning("Fallback download failed: %s", exc)
        return None


# This block only runs when the script is executed directly:
#   python -m src.data.ingest
# It does NOT run when ingest.py is imported by another module (e.g. the Prefect flow)
if __name__ == "__main__":
    # Set up logging to print messages with timestamp and level to the terminal
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    # Run the ingestion and print a summary
    path = ingest()
    df = pd.read_csv(path)
    print(f"\nDataset ready: {path}")
    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"Target column present: {'SalePrice' in df.columns}")
