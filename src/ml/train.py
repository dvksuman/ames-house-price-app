"""
Group 6 — ML Pipeline: Training and Evaluation
Trains Ridge, Lasso, and XGBoost on the Ames Housing encoded dataset.
Outputs: trained models, metrics CSV, feature importance CSV, comparison table.
"""

# --- Imports ---
import pandas as pd          # for loading CSV and building DataFrames
import numpy as np           # for numerical operations (exp, log, etc.)
import os                    # for building file paths
import json                  # for saving metrics as JSON

# scikit-learn tools
from sklearn.model_selection import train_test_split  # splits data into train and test
from sklearn.preprocessing import StandardScaler      # scales features to zero mean, unit variance
from sklearn.linear_model import Ridge, Lasso         # two types of regularised linear regression
from sklearn.metrics import (
    mean_squared_error,   # RMSE base
    mean_absolute_error,  # MAE
    r2_score,             # R² (how much variance the model explains)
)
import joblib              # for saving trained model objects to disk

# XGBoost — gradient-boosted tree model
from xgboost import XGBRegressor

# ---- Paths ----
# Root of the project (two levels up from this file: src/ml/ → src/ → project root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Input: the fully numeric encoded dataset (one-hot + ordinal, log(SalePrice) target)
ENCODED_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "ames_housing_encoded.csv")

# Output directory for saved models and reports
MODELS_DIR = os.path.join(PROJECT_ROOT, "data", "models")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

# Make sure output directories exist before we try to write to them
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---- Helper: MAPE ----
def mean_absolute_percentage_error(y_true, y_pred):
    """
    Computes Mean Absolute Percentage Error.
    Formula: mean(|actual - predicted| / |actual|) * 100
    Works in original dollar scale (not log scale) to give a human-readable % error.
    """
    # Convert to numpy arrays so we can do element-wise division
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    # Divide absolute error by actual value, take the mean, express as percentage
    return float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100)


# ---- Helper: compute all 4 metrics ----
def compute_metrics(y_true_log, y_pred_log, model_name):
    """
    Takes actual and predicted values in log space.
    Computes RMSE and MAE in log space (the model's native space).
    Back-transforms to dollar scale (np.exp) and computes MAPE and dollar RMSE/MAE.
    Returns a dict of all metrics.
    """
    # ---- Log-space metrics ----
    # RMSE in log space: sqrt of mean squared error (lower = better)
    rmse_log = float(np.sqrt(mean_squared_error(y_true_log, y_pred_log)))

    # MAE in log space: mean of absolute differences
    mae_log = float(mean_absolute_error(y_true_log, y_pred_log))

    # R² in log space: 1.0 is perfect, 0.0 means no better than predicting the mean
    r2 = float(r2_score(y_true_log, y_pred_log))

    # ---- Back-transform to original dollar scale using exp() ----
    # log(SalePrice) → SalePrice
    y_true_dollars = np.exp(y_true_log)
    y_pred_dollars = np.exp(y_pred_log)

    # RMSE in dollars
    rmse_dollars = float(np.sqrt(mean_squared_error(y_true_dollars, y_pred_dollars)))

    # MAE in dollars
    mae_dollars = float(mean_absolute_error(y_true_dollars, y_pred_dollars))

    # MAPE in dollars (percentage error, easy to explain to stakeholders)
    mape = mean_absolute_percentage_error(y_true_dollars, y_pred_dollars)

    # Bundle all metrics into a dictionary
    return {
        "model": model_name,
        "RMSE_log": rmse_log,
        "MAE_log": mae_log,
        "R2": r2,
        "RMSE_dollars": rmse_dollars,
        "MAE_dollars": mae_dollars,
        "MAPE_pct": mape,
    }


# ==============================================================================
# TASK 6.1 — Load data and 70/30 train/test split
# ==============================================================================
print("\n=== Task 6.1: Load data and split ===")

# Load the fully encoded CSV (all columns are numeric after one-hot + ordinal encoding)
df = pd.read_csv(ENCODED_CSV)
print(f"Loaded {ENCODED_CSV}: {df.shape[0]} rows × {df.shape[1]} cols")

# One-hot columns were saved as Python bool (True/False) → pandas reads them as object dtype
# Cast every boolean column to integer (1/0) so sklearn can work with them numerically
bool_cols = df.select_dtypes(include="bool").columns.tolist()
df[bool_cols] = df[bool_cols].astype(int)
print(f"Cast {len(bool_cols)} bool columns to int")

# Separate features (X) from target (y)
# Target is LogSalePrice — natural log of the sale price
TARGET = "LogSalePrice"
X = df.drop(columns=[TARGET])   # all columns except the target
y = df[TARGET]                  # just the log-transformed price column

print(f"Features: {X.shape[1]} columns | Target: {TARGET}")

# Split: 70% training, 30% test, same random seed every time (reproducibility)
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.30,        # 30% goes to test set
    random_state=42,       # fixed seed so results are identical across runs
)
print(f"Train: {X_train.shape[0]} rows | Test: {X_test.shape[0]} rows")


# ==============================================================================
# TASK 6.2 — Train Ridge and Lasso (linear models need feature scaling)
# ==============================================================================
print("\n=== Task 6.2: Ridge and Lasso ===")

# Linear models (Ridge, Lasso) penalise large coefficients.
# If features are on very different scales (e.g. lot area in sq ft vs. bedroom count),
# the penalty unfairly shrinks large-scale features more.
# Fix: StandardScaler transforms every feature to mean=0, std=1 at train time.
scaler = StandardScaler()

# Fit the scaler ONLY on training data (never on test data — that would leak test info)
X_train_scaled = scaler.fit_transform(X_train)

# Apply the same scaler to test data (transform only, do not re-fit)
X_test_scaled = scaler.transform(X_test)

# Save the scaler so the API can use it at prediction time
scaler_path = os.path.join(MODELS_DIR, "scaler_ml.joblib")
joblib.dump(scaler, scaler_path)
print(f"Scaler saved to {scaler_path}")

# ---- Ridge regression ----
# Ridge adds L2 penalty (sum of squared coefficients) to the loss function.
# alpha controls how hard the penalty is — higher alpha = smaller coefficients.
ridge = Ridge(alpha=1.0, random_state=42)
ridge.fit(X_train_scaled, y_train)   # train on scaled training features
y_pred_ridge = ridge.predict(X_test_scaled)   # predict on scaled test features

# Save the trained Ridge model
ridge_path = os.path.join(MODELS_DIR, "ridge.joblib")
joblib.dump(ridge, ridge_path)
print(f"Ridge trained and saved to {ridge_path}")

# ---- Lasso regression ----
# Lasso adds L1 penalty (sum of absolute coefficients) to the loss function.
# L1 penalty drives many coefficients exactly to zero — automatic feature selection.
# max_iter increased to 10000 because Lasso can be slow to converge on 215 features.
lasso = Lasso(alpha=0.001, max_iter=10000, random_state=42)
lasso.fit(X_train_scaled, y_train)   # train on scaled training features
y_pred_lasso = lasso.predict(X_test_scaled)   # predict on scaled test features

# Save the trained Lasso model
lasso_path = os.path.join(MODELS_DIR, "lasso.joblib")
joblib.dump(lasso, lasso_path)
print(f"Lasso trained and saved to {lasso_path}")

# Count how many features Lasso zeroed out (a useful diagnostic)
lasso_zeros = int(np.sum(lasso.coef_ == 0))
print(f"Lasso zeroed out {lasso_zeros} of {X.shape[1]} features")


# ==============================================================================
# TASK 6.3 — Train XGBoost (tree models do NOT need scaling)
# ==============================================================================
print("\n=== Task 6.3: XGBoost ===")

# Tree-based models split on feature thresholds, not distances.
# Scaling doesn't change which threshold is best → no scaler needed for XGBoost.
# Use raw encoded features directly (X_train / X_test, not scaled).
xgb = XGBRegressor(
    n_estimators=500,       # number of trees to build
    learning_rate=0.05,     # shrinkage factor per tree (smaller = more robust but slower)
    max_depth=6,            # maximum depth of each tree (controls overfitting)
    subsample=0.8,          # fraction of training rows sampled per tree (reduces overfitting)
    colsample_bytree=0.8,   # fraction of features sampled per tree
    random_state=42,        # fixed seed for reproducibility
    n_jobs=-1,              # use all CPU cores
    verbosity=0,            # suppress XGBoost's internal logging
)

# Train on the raw (unscaled) encoded training features
xgb.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],    # watch test loss during training (for early stopping)
    verbose=False,                  # suppress per-round output
)

# Predict on raw (unscaled) test features
y_pred_xgb = xgb.predict(X_test)

# Save the trained XGBoost model
xgb_path = os.path.join(MODELS_DIR, "xgboost.joblib")
joblib.dump(xgb, xgb_path)
print(f"XGBoost trained ({xgb.n_estimators} trees) and saved to {xgb_path}")


# ==============================================================================
# TASK 6.4 — Compute RMSE, MAE, R², MAPE for each model
# ==============================================================================
print("\n=== Task 6.4: Metrics ===")

# Compute metrics for all three models using our helper function
metrics_ridge = compute_metrics(y_test, y_pred_ridge, "Ridge")
metrics_lasso = compute_metrics(y_test, y_pred_lasso, "Lasso")
metrics_xgb   = compute_metrics(y_test, y_pred_xgb,   "XGBoost")

# Collect into a list for easy DataFrame creation
all_metrics = [metrics_ridge, metrics_lasso, metrics_xgb]

# Print a human-readable summary to the terminal
for m in all_metrics:
    print(
        f"  {m['model']:10s} | "
        f"R²={m['R2']:.4f} | "
        f"RMSE_log={m['RMSE_log']:.4f} | "
        f"RMSE_$={m['RMSE_dollars']:,.0f} | "
        f"MAPE={m['MAPE_pct']:.2f}%"
    )

# Save metrics to CSV for use in the MLflow logging step (Group 7)
metrics_df = pd.DataFrame(all_metrics)
metrics_path = os.path.join(OUTPUT_DIR, "model_metrics.csv")
metrics_df.to_csv(metrics_path, index=False)
print(f"Metrics saved to {metrics_path}")


# ==============================================================================
# TASK 6.5 — Feature importance (top 20 features per model)
# ==============================================================================
print("\n=== Task 6.5: Feature Importance ===")

# Feature names (same order as columns in X)
feature_names = X.columns.tolist()

# ---- Ridge: use absolute coefficient values as importance ----
# A larger absolute coefficient means the feature has a bigger influence on the prediction.
ridge_importance = pd.DataFrame({
    "feature": feature_names,
    "importance": np.abs(ridge.coef_),   # absolute value because sign just means direction
    "model": "Ridge",
})

# ---- Lasso: same as Ridge, but many will be exactly 0 ----
lasso_importance = pd.DataFrame({
    "feature": feature_names,
    "importance": np.abs(lasso.coef_),
    "model": "Lasso",
})

# ---- XGBoost: use built-in feature_importances_ (based on gain) ----
# Gain = total reduction in loss brought by splits on that feature across all trees.
xgb_importance = pd.DataFrame({
    "feature": feature_names,
    "importance": xgb.feature_importances_,
    "model": "XGBoost",
})

# Keep only top 20 features per model (sorted by importance descending)
top_ridge = ridge_importance.nlargest(20, "importance").reset_index(drop=True)
top_lasso = lasso_importance.nlargest(20, "importance").reset_index(drop=True)
top_xgb   = xgb_importance.nlargest(20, "importance").reset_index(drop=True)

# Print top 5 for each model so we can spot-check in the terminal
for name, df_imp in [("Ridge", top_ridge), ("Lasso", top_lasso), ("XGBoost", top_xgb)]:
    print(f"\n  Top 5 features — {name}:")
    for _, row in df_imp.head(5).iterrows():
        print(f"    {row['feature']:40s} {row['importance']:.4f}")

# Stack all three into one CSV (with 'model' column to distinguish them)
importance_df = pd.concat([top_ridge, top_lasso, top_xgb], ignore_index=True)
importance_path = os.path.join(OUTPUT_DIR, "feature_importance.csv")
importance_df.to_csv(importance_path, index=False)
print(f"\nFeature importance saved to {importance_path}")


# ==============================================================================
# TASK 6.6 — Side-by-side model comparison table
# ==============================================================================
print("\n=== Task 6.6: Model Comparison Table ===")

# Pivot the metrics DataFrame so each row is a metric and each column is a model
comparison = metrics_df.set_index("model").T   # T = transpose (swap rows and columns)

# Round to 4 decimal places for readability
comparison = comparison.round(4)

# Print the table to the terminal
print(comparison.to_string())

# Save as CSV for the assignment report and the Streamlit dashboard
comparison_path = os.path.join(OUTPUT_DIR, "model_comparison.csv")
comparison.to_csv(comparison_path)
print(f"\nComparison table saved to {comparison_path}")

# Also save a JSON version so the FastAPI layer can serve it without parsing CSV
comparison_json_path = os.path.join(OUTPUT_DIR, "model_comparison.json")
with open(comparison_json_path, "w") as f:
    # orient="index" → {metric: {model: value}} structure
    json.dump(metrics_df.set_index("model").to_dict(orient="index"), f, indent=2)
print(f"Comparison JSON saved to {comparison_json_path}")

print("\n=== Group 6 complete ===")
