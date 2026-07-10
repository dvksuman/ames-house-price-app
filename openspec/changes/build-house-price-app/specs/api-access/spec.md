## ADDED Requirements

### Requirement: Prediction Endpoint
The system SHALL expose a REST API endpoint that accepts house feature values and returns a predicted sale price using the registered best model.

#### Scenario: Successful prediction
- **WHEN** a client sends a valid set of house features to the prediction endpoint
- **THEN** the API returns a predicted SalePrice value and the identifier of the model version used

#### Scenario: Invalid input rejected
- **WHEN** a client sends a request missing required fields or with invalid types
- **THEN** the API returns a 4xx error describing the validation failure

### Requirement: Built-in Application Details via APIs
The system SHALL expose at least four application/deployment details by wrapping the built-in REST APIs of MLflow and Prefect, rather than hardcoding static metadata.

#### Scenario: Model registry details
- **WHEN** a client requests model information
- **THEN** the API returns the current registered model's name, version, and stage, sourced from the MLflow Model Registry API

#### Scenario: Experiment details
- **WHEN** a client requests experiment information
- **THEN** the API returns the MLflow experiment's name, ID, and latest run summary, sourced from the MLflow Tracking API

#### Scenario: Pipeline/deployment details
- **WHEN** a client requests pipeline information
- **THEN** the API returns the Prefect deployment's name, schedule (every 2 minutes), and flow name, sourced from the Prefect REST API

#### Scenario: Recent pipeline run details
- **WHEN** a client requests recent pipeline run information
- **THEN** the API returns the status and timestamps of the most recent DataOps flow runs, sourced from the Prefect REST API

#### Scenario: Upstream service unavailable
- **WHEN** MLflow or Prefect's server is unreachable when an app-details endpoint is called
- **THEN** the API returns a 503 response with a clear error message instead of crashing

### Requirement: Health Check
The system SHALL expose a health check endpoint reporting service and dependency status.

#### Scenario: Healthy
- **WHEN** a client calls the health endpoint and MLflow/Prefect are reachable
- **THEN** the API returns a 200 status indicating the service and its dependencies are healthy
