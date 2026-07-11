# os lets us create folders and check file paths
import os

# logging lets us print timestamped messages to the terminal
import logging

# numpy provides math functions — we use it for log() and exp()
import numpy as np

# pandas reads and manipulates tabular data
import pandas as pd

# matplotlib is the core plotting library — we use it to save charts as image files
import matplotlib
# Use 'Agg' backend — draws charts to files without needing a screen or display window
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# seaborn builds on matplotlib and makes prettier statistical charts with less code
import seaborn as sns

# configure() applies the Zscaler TLS fix and loads .env
# read_processed_csv() reads CSVs without converting "None" strings to NaN
from src.utils import configure, read_processed_csv
configure()

# Create a logger so all messages are prefixed with this module's name
logger = logging.getLogger(__name__)

# ── paths ─────────────────────────────────────────────────────────────────────

# Input: the cleaned (imputed, unscaled) dataset from Group 3
PROCESSED_PATH = "data/processed/ames_housing_processed.csv"

# Output: fully numeric encoded matrix ready for model training
ENCODED_PATH = "data/processed/ames_housing_encoded.csv"

# Output: top correlated features saved as a CSV for reference
CORR_TOP_PATH = "output/correlation_top.csv"

# Output: folder where all plot images are saved
PLOTS_DIR = "output/plots"

# ── ordinal encoding maps ─────────────────────────────────────────────────────

# These columns use the same quality scale: Excellent → Good → Average → Fair → Poor → None
# We convert the words to numbers so the model understands the ranking
QUALITY_MAP = {"Ex": 5, "Gd": 4, "TA": 3, "Fa": 2, "Po": 1, "None": 0}

# The quality-scale columns that all share the same Ex/Gd/TA/Fa/Po/None values
QUALITY_COLS = [
    "Exter Qual", "Exter Cond", "Bsmt Qual", "Bsmt Cond",
    "Heating QC", "Kitchen Qual", "Fireplace Qu",
    "Garage Qual", "Garage Cond", "Pool QC",
]

# Each of these columns has its own unique ordinal scale
OTHER_ORDINAL = {
    # Basement exposure to walkout/garden: Good > Average > Minimum > No exposure > None
    "Bsmt Exposure":  {"Gd": 4, "Av": 3, "Mn": 2, "No": 1, "None": 0},
    # Basement finished area type — GLQ (Good Living Quarters) is best, Unf is unfinished
    "BsmtFin Type 1": {"GLQ": 6, "ALQ": 5, "BLQ": 4, "Rec": 3, "LwQ": 2, "Unf": 1, "None": 0},
    # Second basement finished area type — same scale
    "BsmtFin Type 2": {"GLQ": 6, "ALQ": 5, "BLQ": 4, "Rec": 3, "LwQ": 2, "Unf": 1, "None": 0},
    # Garage interior finish: Finished > Rough Finished > Unfinished > None
    "Garage Finish":  {"Fin": 3, "RFn": 2, "Unf": 1, "None": 0},
    # Fence quality: Good Privacy > Minimum Privacy > Good Wood > Minimum Wire > None
    # MnWw (Minimum Wire) is the actual code in the data — De Cock's dict says MnWo but data has MnWw
    "Fence":          {"GdPrv": 4, "MnPrv": 3, "GdWo": 2, "MnWw": 1, "None": 0},
    # Lot shape regularity: Regular is best, Irregular 3 is worst
    "Lot Shape":      {"Reg": 4, "IR1": 3, "IR2": 2, "IR3": 1},
    # Land slope: Gentle > Moderate > Severe
    "Land Slope":     {"Gtl": 3, "Mod": 2, "Sev": 1},
    # Paved driveway: Yes > Partial > No
    "Paved Drive":    {"Y": 3, "P": 2, "N": 1},
    # Home functionality: Typical is best, Salvage only is worst
    "Functional":     {"Typ": 8, "Min1": 7, "Min2": 6, "Mod": 5,
                       "Maj1": 4, "Maj2": 3, "Sev": 2, "Sal": 1},
}

# Columns that should be dropped — they are identifiers, not features
DROP_COLS = ["Order", "PID"]


# ── main function ─────────────────────────────────────────────────────────────

def run_eda() -> str:
    # This is the main function — runs all EDA steps and returns path to encoded dataset

    # Create the plots output folder if it doesn't already exist
    os.makedirs(PLOTS_DIR, exist_ok=True)

    # Load the cleaned dataset using our shared reader (preserves "None" strings)
    df = read_processed_csv(PROCESSED_PATH)
    logger.info("Loaded processed data: %d rows x %d cols", len(df), len(df.columns))

    # ── task 4.1: correlation matrix ─────────────────────────────────────────
    # Select only numeric columns for correlation (text columns can't be correlated)
    num_df = df.select_dtypes(include="number")

    # Compute pairwise Pearson correlation between all numeric columns
    corr_matrix = num_df.corr()

    # Extract just the correlation of every column with SalePrice
    # drop("SalePrice") removes SalePrice's correlation with itself (always 1.0)
    saleprice_corr = corr_matrix["SalePrice"].drop("SalePrice")

    # Sort by absolute value so the most correlated features appear first
    saleprice_corr_sorted = saleprice_corr.abs().sort_values(ascending=False)

    # Keep the top 20 most correlated features
    top_features = saleprice_corr_sorted.head(20).index.tolist()

    # Build a report DataFrame with both the raw correlation and the absolute value
    corr_report = pd.DataFrame({
        "correlation": saleprice_corr[top_features],
        "abs_correlation": saleprice_corr_sorted[top_features],
    })

    # Save the correlation report as a CSV file for reference
    corr_report.to_csv(CORR_TOP_PATH)
    logger.info("Saved top correlations → %s", CORR_TOP_PATH)

    # ── task 4.2: categorical feature vs SalePrice ───────────────────────────
    # Analyse Neighbourhood — it has the biggest price spread of any categorical column
    # group-by mean: for each neighbourhood, compute the average SalePrice
    nbhd_mean = df.groupby("Neighborhood")["SalePrice"].mean().sort_values(ascending=False)

    # Log the top 5 and bottom 5 neighbourhoods by average price
    logger.info("Neighbourhood vs SalePrice (top 5):")
    for nbhd, price in nbhd_mean.head(5).items():
        logger.info("  %-15s  $%.0f", nbhd, price)
    logger.info("Neighbourhood vs SalePrice (bottom 5):")
    for nbhd, price in nbhd_mean.tail(5).items():
        logger.info("  %-15s  $%.0f", nbhd, price)

    # ── task 4.3: binning ─────────────────────────────────────────────────────
    # Bin Year Built into era ranges to show how house age relates to price
    # Cut divides the continuous Year Built column into labelled buckets
    era_bins = [0, 1949, 1969, 1989, 2009, 9999]
    era_labels = ["Pre-1950", "1950-1969", "1970-1989", "1990-2009", "2010+"]

    # pd.cut assigns each house to an era bucket based on its Year Built value
    df["Era"] = pd.cut(df["Year Built"], bins=era_bins, labels=era_labels)

    # Count how many houses fall into each era
    era_counts = df["Era"].value_counts().sort_index()
    logger.info("Houses by era (Year Built bins):")
    for era, count in era_counts.items():
        logger.info("  %-12s  %d houses", era, count)

    # ── task 4.4: encoding ───────────────────────────────────────────────────
    # Produce a fully numeric feature matrix for model training
    # Start with a copy so we don't modify the processed dataset
    df_enc = df.copy()

    # Drop the Era column we just added (it was for analysis only, not a model feature)
    df_enc = df_enc.drop(columns=["Era"])

    # Drop identifier columns — they have no predictive value
    df_enc = df_enc.drop(columns=[c for c in DROP_COLS if c in df_enc.columns])

    # Apply quality-scale ordinal encoding to all quality columns
    for col in QUALITY_COLS:
        # Only encode the column if it exists in the dataset
        if col in df_enc.columns:
            # Replace each string value with its numeric rank using the QUALITY_MAP
            df_enc[col] = df_enc[col].map(QUALITY_MAP)

    # Apply other ordinal encodings (each column has its own unique map)
    for col, mapping in OTHER_ORDINAL.items():
        if col in df_enc.columns:
            # Replace each string value with its rank from the column's specific map
            df_enc[col] = df_enc[col].map(mapping)

    # Add log(SalePrice) as the model target
    # np.log() computes the natural logarithm — squishes the skewed price distribution
    df_enc["LogSalePrice"] = np.log(df_enc["SalePrice"])
    logger.info("Added LogSalePrice column (skewness was 1.744 on raw SalePrice)")

    # One-hot encode all remaining text (object/str) columns
    # get_dummies() creates a new column for each unique category value
    # drop_first=True drops the first category to avoid multicollinearity
    # (if we know a house is not in any of N-1 categories, it must be in the Nth)
    df_enc = pd.get_dummies(df_enc, drop_first=True)

    # Log the shape of the encoded matrix so we can see how many columns were created
    logger.info("Encoded dataset shape: %d rows x %d cols", len(df_enc), len(df_enc.columns))

    # Save the fully numeric encoded dataset
    df_enc.to_csv(ENCODED_PATH, index=False)
    logger.info("Saved encoded dataset → %s", ENCODED_PATH)

    # ── task 4.5: univariate plot (SalePrice distribution) ───────────────────
    # Create a new figure with a specific size (width=10 inches, height=4 inches)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # Left chart: raw SalePrice histogram — shows the right-skewed shape
    axes[0].hist(df["SalePrice"], bins=50, color="steelblue", edgecolor="white")
    axes[0].set_title("SalePrice Distribution (raw)")
    axes[0].set_xlabel("Sale Price ($)")
    axes[0].set_ylabel("Number of Houses")

    # Right chart: log(SalePrice) histogram — shows the normalised bell shape
    axes[1].hist(np.log(df["SalePrice"]), bins=50, color="darkorange", edgecolor="white")
    axes[1].set_title("log(SalePrice) Distribution (normalised)")
    axes[1].set_xlabel("log(Sale Price)")
    axes[1].set_ylabel("Number of Houses")

    # Add a title above both charts
    fig.suptitle("SalePrice: Raw vs Log-Transformed", fontsize=13)

    # Adjust spacing so the title doesn't overlap the charts
    plt.tight_layout()

    # Save the chart as a PNG image file
    dist_path = os.path.join(PLOTS_DIR, "saleprice_dist.png")
    plt.savefig(dist_path, dpi=150, bbox_inches="tight")

    # Close the figure to free memory — important when generating multiple plots
    plt.close()
    logger.info("Saved univariate plot → %s", dist_path)

    # ── task 4.6: bivariate plot (top feature vs SalePrice) ──────────────────
    # Gr Liv Area (above-ground living area in sq ft) has the 2nd highest correlation (0.71)
    # and is the most interpretable: bigger house = higher price
    fig, ax = plt.subplots(figsize=(8, 5))

    # Scatter plot: each dot is one house, x=living area, y=sale price
    ax.scatter(df["Gr Liv Area"], df["SalePrice"], alpha=0.3, s=10, color="steelblue")
    ax.set_title("Above-Ground Living Area vs Sale Price\n(correlation = 0.71)")
    ax.set_xlabel("Gr Liv Area (sq ft)")
    ax.set_ylabel("Sale Price ($)")

    # Format y-axis with dollar signs and commas (e.g. $200,000)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    plt.tight_layout()

    # Save the bivariate scatter plot
    scatter_path = os.path.join(PLOTS_DIR, "top_feature_scatter.png")
    plt.savefig(scatter_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved bivariate plot → %s", scatter_path)

    # ── task 4.7: correlation heatmap (top 15 features) ──────────────────────
    # Pick the top 15 numeric features most correlated with SalePrice
    top15 = saleprice_corr_sorted.head(15).index.tolist()

    # Include SalePrice itself so the heatmap shows correlations with the target
    heatmap_cols = top15 + ["SalePrice"]

    # Compute the correlation matrix for just these 16 columns
    corr_subset = num_df[heatmap_cols].corr()

    # Create a large figure so the heatmap labels are readable
    fig, ax = plt.subplots(figsize=(12, 10))

    # Draw the heatmap: annot=True shows the correlation number in each cell
    # fmt=".2f" formats numbers to 2 decimal places
    # cmap="coolwarm" uses blue for negative, red for positive correlations
    sns.heatmap(
        corr_subset,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        ax=ax,
    )
    ax.set_title("Correlation Heatmap — Top 15 Features vs SalePrice", fontsize=13)
    plt.tight_layout()

    # Save the heatmap
    heatmap_path = os.path.join(PLOTS_DIR, "correlation_heatmap.png")
    plt.savefig(heatmap_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved correlation heatmap → %s", heatmap_path)

    # Return the path to the encoded dataset so callers know where it is
    return ENCODED_PATH


# ── run directly ──────────────────────────────────────────────────────────────

# This block runs only when you execute: python -m src.eda.eda
# It does NOT run when this file is imported by another module
if __name__ == "__main__":
    # Set up logging to print timestamped messages to the terminal
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    # Run EDA and print a summary
    path = run_eda()
    df_enc = pd.read_csv(path)
    print(f"\nEDA complete.")
    print(f"Encoded dataset: {path}")
    print(f"Shape: {df_enc.shape[0]} rows x {df_enc.shape[1]} cols")
    print(f"\nOutputs written:")
    print(f"  {CORR_TOP_PATH}")
    print(f"  {PLOTS_DIR}/saleprice_dist.png")
    print(f"  {PLOTS_DIR}/top_feature_scatter.png")
    print(f"  {PLOTS_DIR}/correlation_heatmap.png")
    print(f"  {ENCODED_PATH}")
