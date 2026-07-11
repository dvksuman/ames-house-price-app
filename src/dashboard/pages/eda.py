"""
Task 9.1 — EDA View
Displays summary statistics and pre-generated charts from the data pipeline.
All data comes from the FastAPI backend — no direct dataset access here.
"""

# Import Streamlit for building the web UI.
import streamlit as st

# Import our API client — the only place HTTP calls are made.
import sys
import os
# Add the src directory to the path so we can import api_client.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.api_client import get_eda_charts, get_eda_summary

# Import base64 and PIL for decoding and displaying the chart images.
import base64
from PIL import Image
import io


def show():
    """Render the full EDA page."""

    # Page title shown at the top of the view.
    st.title("Exploratory Data Analysis")
    st.markdown("All charts and statistics are sourced from the FastAPI backend — no direct dataset access.")

    # ---- SUMMARY STATS SECTION ----
    st.header("Summary Statistics")

    # Try to fetch the summary stats from the API.
    try:
        # Call the API to get summary stats and top correlations.
        summary_data = get_eda_summary()

        # Pull out the two parts of the response.
        summary_stats = summary_data.get("summary_stats", {})
        correlations = summary_data.get("top_correlations_with_saleprice", {})

        # Display summary stats as a table if we got data back.
        if summary_stats:
            # Import pandas to convert the nested dict to a DataFrame for display.
            import pandas as pd
            # The summary_stats dict is structured as {column: {stat: value}}.
            stats_df = pd.DataFrame(summary_stats)
            # Show the table — use_container_width makes it fill the full page width.
            st.dataframe(stats_df, use_container_width=True)
        else:
            st.warning("No summary stats returned from the API.")

        # Display top correlations as a bar chart.
        if correlations:
            st.subheader("Top Features Correlated with Sale Price")
            import pandas as pd
            # Convert the correlations dict to a DataFrame for Streamlit's bar chart.
            corr_df = pd.DataFrame(
                list(correlations.items()),
                columns=["Feature", "Correlation with SalePrice"]
            ).set_index("Feature")
            # Draw the horizontal bar chart.
            st.bar_chart(corr_df)

    except Exception as e:
        # Show a user-friendly error if the API is down or hasn't run yet.
        st.error(f"Could not load summary stats from API: {e}")

    # ---- CHARTS SECTION ----
    st.header("EDA Charts")

    # Try to fetch the pre-generated chart images from the API.
    try:
        # Call the API — returns a dict of {chart_name: base64_string}.
        charts = get_eda_charts()

        # Give each chart a human-readable title for display.
        chart_titles = {
            "saleprice_dist": "Sale Price Distribution",
            "correlation_heatmap": "Feature Correlation Heatmap",
            "top_feature_scatter": "Top Feature vs Sale Price",
        }

        # Loop through each chart and display it.
        for chart_name, b64_string in charts.items():
            # Get the human-readable title, or fall back to the file name.
            title = chart_titles.get(chart_name, chart_name.replace("_", " ").title())
            st.subheader(title)

            # Decode the base64 string back to raw image bytes.
            image_bytes = base64.b64decode(b64_string)

            # Open the bytes as a PIL image object.
            image = Image.open(io.BytesIO(image_bytes))

            # Display the image in the Streamlit app.
            st.image(image, use_container_width=True)

    except Exception as e:
        # Show an error if charts can't be fetched.
        st.error(f"Could not load charts from API: {e}")
        st.info("Make sure the FastAPI server is running and the EDA pipeline has been executed.")
