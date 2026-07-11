"""
Group 9 — Streamlit Dashboard
Entry point for the Ames Housing Price Predictor dashboard.
Navigation is via the sidebar — each page is a separate module.
ALL data comes from the FastAPI backend (localhost:8000); no direct file/model access.
"""

# Import Streamlit — the framework that turns Python into a web app.
import streamlit as st

# Add the project src directory to the Python path so page imports work.
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import the three page modules — each has a show() function.
from dashboard.pages import eda, prediction, app_details


# ---- PAGE CONFIG ----
# Must be the very first Streamlit call in the script.
st.set_page_config(
    page_title="Ames House Price Predictor",  # browser tab title
    page_icon="🏠",                           # emoji shown in browser tab
    layout="wide",                            # use the full page width
)


# ---- SIDEBAR NAVIGATION ----
st.sidebar.title("🏠 Ames Predictor")
st.sidebar.markdown("---")

# Radio buttons let the user pick which view to show.
page = st.sidebar.radio(
    "Navigate to",
    options=["EDA", "Predict Price", "App Details"],
    index=0,  # default to the EDA page
)

# Show a small note at the bottom of the sidebar.
st.sidebar.markdown("---")
st.sidebar.caption("All data sourced via FastAPI (localhost:8000)")


# ---- PAGE ROUTING ----
# Call the show() function of whichever page the user selected.
if page == "EDA":
    # Show the exploratory data analysis view.
    eda.show()

elif page == "Predict Price":
    # Show the house price prediction form.
    prediction.show()

elif page == "App Details":
    # Show the live application details (MLflow, Prefect, health).
    app_details.show()
