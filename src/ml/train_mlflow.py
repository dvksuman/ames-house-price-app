"""
Group 7 — MLflow Tracking
Re-trains Ridge, Lasso, and XGBoost (same settings as Group 6) and logs every run
to MLflow: hyperparameters, all 4 metrics, and the model artifact.
Registers XGBoost (best model) in the MLflow Model Registry with alias "production".
"""

# --- Standard library ---
import os       # for building file paths
import numpy as np  # for exp() when back-transforming log predictions

# --- scikit-learn ---
from sklearn.model_selection import train_test_split  # 70/30 split
from sklearn.preprocessing import StandardScaler      # scale features for linear models
from sklearn.linear_model import Ridge, Lasso         # regularised linear models
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score  # evaluation

# --- XGBoost ---
from xgboost import XGBRegressor  # gradient-boosted tree model

# --- Data ---
import pandas as pd  # read CSV

# --- MLflow ---
import mlflow                       # main MLflow library
import mlflow.sklearn               # flavour for scikit-learn models (Ridge, Lasso)
import mlflow.xgboost               # flavour for XGBoost models
from mlflow import MlflowClient     # client for Model Registry operations


# ==============================================================================
# TASK 7.1 — Configure MLflow tracking URI (local SQLite backend)
# ==============================================================================

# Build an absolute path to the project root so the DB lands there regardless
# of which directory the user runs this script from.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# The SQLite database file that MLflow will write all experiment data to.
# "sqlite:///..." requires a triple-slash prefix — MLflow's URI convention.
DB_PATH = os.path.join(PROJECT_ROOT, "mlruns.db")

# Tell MLflow where to save experiment data (the logbook address).
mlflow.set_tracking_uri(f"sqlite:///{DB_PATH}")
print(f"MLflow tracking URI: sqlite:///{DB_PATH}")

# Name this experiment — all three runs will appear under this name in the UI.
EXPERIMENT_NAME = "ames-housing-price-prediction"

# Create the experiment if it doesn't exist yet, or reuse it if it does.
mlflow.set_experiment(EXPERIMENT_NAME)
print(f"MLflow experiment: {EXPERIMENT_NAME}")


# ==============================================================================
# Shared setup — same data and split used in Group 6 (same seed = same results)
# ==============================================================================

# Path to the fully numeric encoded dataset produced in Group 4.
ENCODED_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "ames_housing_encoded.csv")

# Load the dataset.
df = pd.read_csv(ENCODED_CSV)
print(f"\nLoaded {ENCODED_CSV}: {df.shape[0]} rows × {df.shape[1]} cols")

# One-hot columns were saved as Python booleans; cast to int so sklearn accepts them.
bool_cols = df.select_dtypes(include="bool").columns.tolist()
df[bool_cols] = df[bool_cols].astype(int)

# Separate features from the log-transformed target.
TARGET = "LogSalePrice"
X = df.drop(columns=[TARGET])   # all input columns
y = df[TARGET]                  # log(SalePrice) — what we're predicting

# 70/30 split with a fixed seed so every run gives identical train/test rows.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.30, random_state=42
)
print(f"Train: {X_train.shape[0]} rows | Test: {X_test.shape[0]} rows")

# Scale features for linear models (Ridge/Lasso).
# Fitted on training data only to avoid leaking test statistics.
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)  # fit + transform training set
X_test_scaled  = scaler.transform(X_test)       # transform test set with same scale


# ==============================================================================
# Helper — compute all 4 required metrics from log-space predictions
# ==============================================================================

def compute_metrics(y_true_log, y_pred_log):
    """
    Returns a dict with R², RMSE (dollars), MAE (dollars), MAPE (%) and
    the two log-space metrics.  Inputs are log(SalePrice) arrays.
    """
    # Metrics in log space (model's native space).
    rmse_log = float(np.sqrt(mean_squared_error(y_true_log, y_pred_log)))
    mae_log  = float(mean_absolute_error(y_true_log, y_pred_log))
    r2       = float(r2_score(y_true_log, y_pred_log))

    # Back-transform to dollar scale for human-readable metrics.
    y_true_d = np.exp(y_true_log)
    y_pred_d = np.exp(y_pred_log)

    rmse_d = float(np.sqrt(mean_squared_error(y_true_d, y_pred_d)))
    mae_d  = float(mean_absolute_error(y_true_d, y_pred_d))
    mape   = float(np.mean(np.abs((y_true_d - y_pred_d) / y_true_d)) * 100)

    # Bundle into a plain dictionary for easy mlflow.log_metrics() calls.
    return {
        "R2":           r2,
        "RMSE_dollars": rmse_d,
        "MAE_dollars":  mae_d,
        "MAPE_pct":     mape,
        "RMSE_log":     rmse_log,
        "MAE_log":      mae_log,
    }


# ==============================================================================
# TASK 7.2 — Log each model to MLflow as a separate run
# ==============================================================================

print("\n=== Task 7.2: Logging runs to MLflow ===")

# We will store the XGBoost run's URI here so we can register it in task 7.3.
xgb_model_uri = None

# ---- Run 1: Ridge ----
print("\n  [1/3] Ridge ...")
with mlflow.start_run(run_name="Ridge"):

    # Train the model (same hyperparameters as Group 6).
    ridge = Ridge(alpha=1.0, random_state=42)
    ridge.fit(X_train_scaled, y_train)
    y_pred = ridge.predict(X_test_scaled)

    # Log the hyperparameter (the setting we chose before training).
    mlflow.log_param("model_type", "Ridge")
    mlflow.log_param("alpha", 1.0)

    # Log all 4 required metrics (plus the log-space ones for completeness).
    metrics = compute_metrics(y_test.values, y_pred)
    mlflow.log_metrics(metrics)  # logs every key-value pair in the dict at once

    # Log the trained model file as an MLflow artifact using the sklearn flavour.
    mlflow.sklearn.log_model(ridge, name="model")

    print(f"    R²={metrics['R2']:.4f}  RMSE=${metrics['RMSE_dollars']:,.0f}  MAPE={metrics['MAPE_pct']:.2f}%")

# ---- Run 2: Lasso ----
print("  [2/3] Lasso ...")
with mlflow.start_run(run_name="Lasso"):

    # Train the model.
    lasso = Lasso(alpha=0.001, max_iter=10000, random_state=42)
    lasso.fit(X_train_scaled, y_train)
    y_pred = lasso.predict(X_test_scaled)

    # Log hyperparameters.
    mlflow.log_param("model_type", "Lasso")
    mlflow.log_param("alpha", 0.001)
    mlflow.log_param("max_iter", 10000)

    # Log metrics.
    metrics = compute_metrics(y_test.values, y_pred)
    mlflow.log_metrics(metrics)

    # Log the model artifact.
    mlflow.sklearn.log_model(lasso, name="model")

    print(f"    R²={metrics['R2']:.4f}  RMSE=${metrics['RMSE_dollars']:,.0f}  MAPE={metrics['MAPE_pct']:.2f}%")

# ---- Run 3: XGBoost ----
print("  [3/3] XGBoost ...")
with mlflow.start_run(run_name="XGBoost") as xgb_run:

    # Train the model — tree models do NOT need scaled features.
    xgb = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    y_pred = xgb.predict(X_test)

    # Log all hyperparameters.
    mlflow.log_param("model_type", "XGBoost")
    mlflow.log_param("n_estimators", 500)
    mlflow.log_param("learning_rate", 0.05)
    mlflow.log_param("max_depth", 6)
    mlflow.log_param("subsample", 0.8)
    mlflow.log_param("colsample_bytree", 0.8)

    # Log metrics.
    metrics = compute_metrics(y_test.values, y_pred)
    mlflow.log_metrics(metrics)

    # Log using the XGBoost flavour — saves in the native XGBoost format.
    mlflow.xgboost.log_model(xgb, name="model")

    # Also log the feature importance CSV from Group 6 as an extra artifact.
    importance_csv = os.path.join(PROJECT_ROOT, "output", "feature_importance.csv")
    if os.path.exists(importance_csv):
        mlflow.log_artifact(importance_csv)  # attaches the file to this run

    # Build the model URI we'll need for the Model Registry step below.
    # Format: "runs:/<run_id>/model"
    xgb_model_uri = f"runs:/{xgb_run.info.run_id}/model"

    print(f"    R²={metrics['R2']:.4f}  RMSE=${metrics['RMSE_dollars']:,.0f}  MAPE={metrics['MAPE_pct']:.2f}%")

print("\nAll 3 runs logged to MLflow.")


# ==============================================================================
# TASK 7.3 — Register XGBoost in the MLflow Model Registry
# ==============================================================================

print("\n=== Task 7.3: Registering XGBoost in Model Registry ===")

# The registered model name — this is the name that FastAPI will use in Group 8
# to load the model at startup.
REGISTERED_MODEL_NAME = "AmesPricePredictor"

# Register the XGBoost run's model artifact under the chosen name.
# This creates version 1 of "AmesPricePredictor" in the registry.
model_version = mlflow.register_model(
    model_uri=xgb_model_uri,            # the run URI we saved above
    name=REGISTERED_MODEL_NAME,         # the name for this model in the registry
)
print(f"Registered '{REGISTERED_MODEL_NAME}' version {model_version.version}")

# Set the alias "production" on this version.
# In MLflow 2.9+ aliases replace the old Staging/Production stage system.
# The alias "production" is a label you stick on a specific version — like a Git tag.
client = MlflowClient()
client.set_registered_model_alias(
    name=REGISTERED_MODEL_NAME,         # which registered model
    alias="production",                 # the label we're attaching
    version=model_version.version,      # which version gets the label
)
print(f"Alias 'production' set on version {model_version.version}")

print("\n=== Group 7 (7.1–7.3) complete ===")
print(f"\nTo verify in the UI, run:")
print(f"  cd {PROJECT_ROOT}")
print(f"  .venv/bin/mlflow ui --backend-store-uri sqlite:///mlruns.db --port 5000")
print(f"  Then open http://localhost:5000")
