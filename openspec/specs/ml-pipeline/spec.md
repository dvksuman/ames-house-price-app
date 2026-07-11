# ml-pipeline Specification

## Purpose
TBD - created by archiving change build-house-price-app. Update Purpose after archive.
## Requirements
### Requirement: Model Selection
The system SHALL use two distinct machine learning algorithms suited to a regression problem: a regularized linear model (Ridge or Lasso) and a gradient-boosted tree ensemble (XGBoost).

#### Scenario: Two algorithms trained
- **WHEN** the training pipeline runs
- **THEN** it fits both a Ridge/Lasso linear regression model and an XGBoost regression model on the same target (SalePrice)

### Requirement: Train/Test Split
The system SHALL split the dataset into 70% training and 30% testing sets before fitting any model.

#### Scenario: Correct split ratio
- **WHEN** the dataset is split
- **THEN** the training set contains approximately 70% of records and the testing set contains approximately 30%, with a fixed random seed for reproducibility

### Requirement: Model Evaluation
The system SHALL evaluate each trained model on the held-out test set using regression metrics.

#### Scenario: Metrics computed on test set
- **WHEN** a model finishes training
- **THEN** the system computes RMSE, MAE, and R² on the test set predictions

#### Scenario: Model comparison
- **WHEN** both models have been evaluated
- **THEN** the system reports a side-by-side comparison of their metrics to identify the better-performing model

### Requirement: MLOps Tracking and Monitoring
The system SHALL track model training runs, log at least four metrics per run, and register models via MLflow.

#### Scenario: Experiment tracking
- **WHEN** a model is trained
- **THEN** the system logs the run's hyperparameters, at least four metrics (e.g. RMSE, MAE, R², MAPE), and the trained model artifact to MLflow

#### Scenario: Model registry
- **WHEN** a training run produces a model that improves on or matches the current best
- **THEN** the system registers that model version in the MLflow Model Registry

#### Scenario: Metrics retrievable for monitoring
- **WHEN** a user queries MLflow (UI or API) for a given run
- **THEN** they can view all logged metrics, parameters, and the associated model artifact

