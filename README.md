# House Price Prediction — API-Driven Cloud-Native App

Coursework project for AIMLCZG549 (API-Driven Cloud Native Solutions), Assignment I.

## Business Understanding

**Problem statement:** Estimating a house's sale price accurately, from its physical
and locational characteristics, is a recurring and high-stakes decision problem in
residential real estate — mispricing a listing either leaves money on the table or
causes it to sit unsold.

**Objective:** Build a regression model that predicts a house's `SalePrice` from its
features (lot size, quality ratings, square footage, neighborhood, etc.), and expose
that model as a monitored, API-accessible service rather than a one-off notebook.

**Stakeholders:**
- **Home sellers / real estate agents** — need a data-driven starting point for
  listing price, instead of relying purely on manual comparables.
- **Mortgage lenders / appraisers** — benefit from an independent, consistent
  price estimate to sanity-check appraisals and reduce over-lending risk.
- **Home buyers** — can use a predicted price to judge whether an asking price is
  reasonable relative to the house's actual characteristics.

## Dataset

Ames Housing dataset (full, ~2,930 records, ~80 features), sourced via Kaggle
(falls back to a public CSV mirror if Kaggle credentials aren't configured).
See [`openspec/changes/build-house-price-app/design.md`](openspec/changes/build-house-price-app/design.md)
for why this dataset (not the smaller 1,460-row competition split) was chosen.

## Architecture

Four local Docker Compose services: FastAPI (prediction + app-info API), Streamlit
(API-driven dashboard), Prefect server (scheduled DataOps pipeline, every 2 minutes),
MLflow server (experiment tracking + model registry). See `design.md` for the full
diagram and rationale.

## Project status

This project is built via [OpenSpec](openspec/) spec-driven development — see
[`CLAUDE.md`](CLAUDE.md) for the enforcement rule and
[`openspec/changes/build-house-price-app/`](openspec/changes/build-house-price-app/)
for the current change (proposal, design, specs, tasks). Run instructions will be
added here as each part of the stack is built.
