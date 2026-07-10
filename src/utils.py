# truststore teaches Python to trust the company's security certificate (Zscaler)
import truststore

# load_dotenv reads the .env file and makes its values available as environment variables
from dotenv import load_dotenv

# pandas reads CSV files into DataFrames
import pandas as pd


def configure():
    # This function is called once at the start of every script that makes internet calls
    # or reads config values. Think of it as "turn on the lights before doing any work."

    # Tell Python to use macOS's own certificate trust store (which already trusts Zscaler)
    # Without this line, Python rejects Kaggle/MLflow HTTPS connections on this machine
    truststore.inject_into_ssl()

    # Read the .env file from the project root and load its key=value pairs
    # into the environment so os.environ.get("KEY") works anywhere in the code
    load_dotenv()


def read_processed_csv(path: str) -> pd.DataFrame:
    # Read a processed CSV file without converting "None" strings back to NaN
    # By default pandas treats "None", "NA", "null" etc. as missing values
    # Our processed CSVs use "None" as a real category value (means "house has no such feature")
    # keep_default_na=False: disable pandas' built-in NA string detection
    # na_values=[""]: only treat empty cells (blank fields) as NaN
    return pd.read_csv(path, keep_default_na=False, na_values=[""])
