"""
Task 9.2 — Prediction View
Lets the user fill in key house features and get a predicted sale price
by calling POST /predict on the FastAPI backend.
All 213 features are sent — user fills ~10, the rest get sensible median defaults.
"""

# Import Streamlit for building the web UI.
import streamlit as st

# Import our API client — all HTTP calls go through here.
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dashboard.api_client import predict


# ---- DEFAULTS ----
# Median values from the Ames dataset for every one of the 213 model features.
# When the user doesn't fill in a field, we use these values instead of 0.
# This gives more realistic predictions than leaving everything at zero.
DEFAULTS = {
    # Key numeric/ordinal features — shown in the form.
    "MS_SubClass": 20.0,
    "Lot_Frontage": 69.0,
    "Lot_Area": 9460.0,
    "Lot_Shape": 3.0,           # 3 = Regular (most common after encoding)
    "Land_Slope": 0.0,
    "Overall_Qual": 6.0,        # shown in form
    "Overall_Cond": 5.0,
    "Year_Built": 1973.0,       # shown in form
    "Year_Remod_Add": 1993.0,
    "Mas_Vnr_Area": 0.0,
    "Exter_Qual": 2.0,
    "Exter_Cond": 2.0,
    "Bsmt_Qual": 3.0,
    "Bsmt_Cond": 3.0,
    "Bsmt_Exposure": 0.0,
    "BsmtFin_Type_1": 0.0,
    "BsmtFin_SF_1": 368.0,
    "BsmtFin_Type_2": 0.0,
    "BsmtFin_SF_2": 0.0,
    "Bsmt_Unf_SF": 467.0,
    "Total_Bsmt_SF": 990.0,     # shown in form
    "Heating_QC": 4.0,
    "First_Flr_SF": 1084.0,     # shown in form
    "Second_Flr_SF": 0.0,
    "Low_Qual_Fin_SF": 0.0,
    "Gr_Liv_Area": 1442.0,      # shown in form
    "Bsmt_Full_Bath": 0.0,
    "Bsmt_Half_Bath": 0.0,
    "Full_Bath": 2.0,           # shown in form
    "Half_Bath": 0.0,
    "Bedroom_AbvGr": 3.0,       # shown in form
    "Kitchen_AbvGr": 1.0,
    "Kitchen_Qual": 2.0,
    "TotRms_AbvGrd": 6.0,
    "Functional": 6.0,
    "Fireplaces": 1.0,
    "Fireplace_Qu": 2.0,
    "Garage_Yr_Blt": 1980.0,
    "Garage_Finish": 1.0,
    "Garage_Cars": 2.0,         # shown in form
    "Garage_Area": 480.0,       # shown in form
    "Garage_Qual": 3.0,
    "Garage_Cond": 3.0,
    "Paved_Drive": 2.0,
    "Wood_Deck_SF": 0.0,
    "Open_Porch_SF": 27.0,
    "Enclosed_Porch": 0.0,
    "Three_Ssn_Porch": 0.0,
    "Screen_Porch": 0.0,
    "Pool_Area": 0.0,
    "Pool_QC": 0.0,
    "Fence": 0.0,
    "Misc_Val": 0.0,
    "Mo_Sold": 6.0,
    "Yr_Sold": 2008.0,
    # One-hot encoded categoricals — all default to 0 (= most common category absent).
    # The "normal" / most common category is represented by all zeros (reference category).
    "MS_Zoning_C_all": 0.0, "MS_Zoning_FV": 0.0, "MS_Zoning_I_all": 0.0,
    "MS_Zoning_RH": 0.0, "MS_Zoning_RL": 1.0, "MS_Zoning_RM": 0.0,
    "Street_Pave": 1.0,
    "Alley_None": 1.0, "Alley_Pave": 0.0,
    "Land_Contour_HLS": 0.0, "Land_Contour_Low": 0.0, "Land_Contour_Lvl": 1.0,
    "Utilities_NoSeWa": 0.0, "Utilities_NoSewr": 0.0,
    "Lot_Config_CulDSac": 0.0, "Lot_Config_FR2": 0.0,
    "Lot_Config_FR3": 0.0, "Lot_Config_Inside": 1.0,
    "Neighborhood_Blueste": 0.0, "Neighborhood_BrDale": 0.0,
    "Neighborhood_BrkSide": 0.0, "Neighborhood_ClearCr": 0.0,
    "Neighborhood_CollgCr": 0.0, "Neighborhood_Crawfor": 0.0,
    "Neighborhood_Edwards": 0.0, "Neighborhood_Gilbert": 0.0,
    "Neighborhood_Greens": 0.0, "Neighborhood_GrnHill": 0.0,
    "Neighborhood_IDOTRR": 0.0, "Neighborhood_Landmrk": 0.0,
    "Neighborhood_MeadowV": 0.0, "Neighborhood_Mitchel": 0.0,
    "Neighborhood_NAmes": 1.0,  # default to NAmes (most common neighborhood)
    "Neighborhood_NPkVill": 0.0, "Neighborhood_NWAmes": 0.0,
    "Neighborhood_NoRidge": 0.0, "Neighborhood_NridgHt": 0.0,
    "Neighborhood_OldTown": 0.0, "Neighborhood_SWISU": 0.0,
    "Neighborhood_Sawyer": 0.0, "Neighborhood_SawyerW": 0.0,
    "Neighborhood_Somerst": 0.0, "Neighborhood_StoneBr": 0.0,
    "Neighborhood_Timber": 0.0, "Neighborhood_Veenker": 0.0,
    "Condition_1_Feedr": 0.0, "Condition_1_Norm": 1.0,
    "Condition_1_PosA": 0.0, "Condition_1_PosN": 0.0,
    "Condition_1_RRAe": 0.0, "Condition_1_RRAn": 0.0,
    "Condition_1_RRNe": 0.0, "Condition_1_RRNn": 0.0,
    "Condition_2_Feedr": 0.0, "Condition_2_Norm": 1.0,
    "Condition_2_PosA": 0.0, "Condition_2_PosN": 0.0,
    "Condition_2_RRAe": 0.0, "Condition_2_RRAn": 0.0, "Condition_2_RRNn": 0.0,
    "Bldg_Type_2fmCon": 0.0, "Bldg_Type_Duplex": 0.0,
    "Bldg_Type_Twnhs": 0.0, "Bldg_Type_TwnhsE": 0.0,
    "House_Style_1_5Unf": 0.0, "House_Style_1Story": 1.0,
    "House_Style_2_5Fin": 0.0, "House_Style_2_5Unf": 0.0,
    "House_Style_2Story": 0.0, "House_Style_SFoyer": 0.0, "House_Style_SLvl": 0.0,
    "Roof_Style_Gable": 1.0, "Roof_Style_Gambrel": 0.0, "Roof_Style_Hip": 0.0,
    "Roof_Style_Mansard": 0.0, "Roof_Style_Shed": 0.0,
    "Roof_Matl_CompShg": 1.0, "Roof_Matl_Membran": 0.0, "Roof_Matl_Metal": 0.0,
    "Roof_Matl_Roll": 0.0, "Roof_Matl_TarGrv": 0.0,
    "Roof_Matl_WdShake": 0.0, "Roof_Matl_WdShngl": 0.0,
    "Exterior_1st_AsphShn": 0.0, "Exterior_1st_BrkComm": 0.0,
    "Exterior_1st_BrkFace": 0.0, "Exterior_1st_CBlock": 0.0,
    "Exterior_1st_CemntBd": 0.0, "Exterior_1st_HdBoard": 0.0,
    "Exterior_1st_ImStucc": 0.0, "Exterior_1st_MetalSd": 1.0,
    "Exterior_1st_Plywood": 0.0, "Exterior_1st_PreCast": 0.0,
    "Exterior_1st_Stone": 0.0, "Exterior_1st_Stucco": 0.0,
    "Exterior_1st_VinylSd": 0.0, "Exterior_1st_WdSdng": 0.0,
    "Exterior_1st_WdShing": 0.0,
    "Exterior_2nd_AsphShn": 0.0, "Exterior_2nd_BrkCmn": 0.0,
    "Exterior_2nd_BrkFace": 0.0, "Exterior_2nd_CBlock": 0.0,
    "Exterior_2nd_CmentBd": 0.0, "Exterior_2nd_HdBoard": 0.0,
    "Exterior_2nd_ImStucc": 0.0, "Exterior_2nd_MetalSd": 1.0,
    "Exterior_2nd_Other": 0.0, "Exterior_2nd_Plywood": 0.0,
    "Exterior_2nd_PreCast": 0.0, "Exterior_2nd_Stone": 0.0,
    "Exterior_2nd_Stucco": 0.0, "Exterior_2nd_VinylSd": 0.0,
    "Exterior_2nd_WdSdng": 0.0, "Exterior_2nd_WdShng": 0.0,
    "Mas_Vnr_Type_BrkFace": 0.0, "Mas_Vnr_Type_CBlock": 0.0,
    "Mas_Vnr_Type_None": 1.0, "Mas_Vnr_Type_Stone": 0.0,
    "Foundation_CBlock": 1.0, "Foundation_PConc": 0.0,
    "Foundation_Slab": 0.0, "Foundation_Stone": 0.0, "Foundation_Wood": 0.0,
    "Heating_GasA": 1.0, "Heating_GasW": 0.0, "Heating_Grav": 0.0,
    "Heating_OthW": 0.0, "Heating_Wall": 0.0,
    "Central_Air_Y": 1.0,
    "Electrical_FuseF": 0.0, "Electrical_FuseP": 0.0,
    "Electrical_Mix": 0.0, "Electrical_SBrkr": 1.0,
    "Garage_Type_Attchd": 1.0, "Garage_Type_Basment": 0.0,
    "Garage_Type_BuiltIn": 0.0, "Garage_Type_CarPort": 0.0,
    "Garage_Type_Detchd": 0.0, "Garage_Type_None": 0.0,
    "Misc_Feature_Gar2": 0.0, "Misc_Feature_None": 1.0,
    "Misc_Feature_Othr": 0.0, "Misc_Feature_Shed": 0.0, "Misc_Feature_TenC": 0.0,
    "Sale_Type_CWD": 0.0, "Sale_Type_Con": 0.0, "Sale_Type_ConLD": 0.0,
    "Sale_Type_ConLI": 0.0, "Sale_Type_ConLw": 0.0, "Sale_Type_New": 0.0,
    "Sale_Type_Oth": 0.0, "Sale_Type_VWD": 0.0, "Sale_Type_WD": 1.0,
    "Sale_Condition_AdjLand": 0.0, "Sale_Condition_Alloca": 0.0,
    "Sale_Condition_Family": 0.0, "Sale_Condition_Normal": 1.0,
    "Sale_Condition_Partial": 0.0,
}

# Neighborhood options shown in the dropdown — maps display name → Pydantic field name.
NEIGHBORHOOD_OPTIONS = {
    "NAmes (North Ames)": "Neighborhood_NAmes",
    "CollgCr (College Creek)": "Neighborhood_CollgCr",
    "OldTown": "Neighborhood_OldTown",
    "Edwards": "Neighborhood_Edwards",
    "Somerst (Somerset)": "Neighborhood_Somerst",
    "NridgHt (Northridge Heights)": "Neighborhood_NridgHt",
    "Gilbert": "Neighborhood_Gilbert",
    "Sawyer": "Neighborhood_Sawyer",
    "NWAmes (NW Ames)": "Neighborhood_NWAmes",
    "SawyerW (Sawyer West)": "Neighborhood_SawyerW",
    "BrkSide (Brookside)": "Neighborhood_BrkSide",
    "Crawfor (Crawford)": "Neighborhood_Crawfor",
    "Mitchel (Mitchell)": "Neighborhood_Mitchel",
    "NoRidge (Northridge)": "Neighborhood_NoRidge",
    "Timber": "Neighborhood_Timber",
    "IDOTRR": "Neighborhood_IDOTRR",
    "ClearCr (Clear Creek)": "Neighborhood_ClearCr",
    "StoneBr (Stone Brook)": "Neighborhood_StoneBr",
    "MeadowV (Meadow Village)": "Neighborhood_MeadowV",
    "BrDale (Briardale)": "Neighborhood_BrDale",
    "Veenker": "Neighborhood_Veenker",
    "Blueste (Bluestem)": "Neighborhood_Blueste",
    "Greens": "Neighborhood_Greens",
    "NPkVill (Northpark Villa)": "Neighborhood_NPkVill",
    "SWISU": "Neighborhood_SWISU",
    "GrnHill (Green Hills)": "Neighborhood_GrnHill",
    "Landmrk (Landmark)": "Neighborhood_Landmrk",
}


def show():
    """Render the prediction form and result."""

    # Page title.
    st.title("House Price Prediction")
    st.markdown(
        "Fill in the key features below. The remaining 200+ features use "
        "dataset median values as defaults. Click **Predict** to get a price estimate."
    )

    # ---- FORM ----
    # Use a Streamlit form so the prediction only fires when the user clicks Submit.
    with st.form("prediction_form"):

        # Divide the form into two columns so it isn't one long vertical list.
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Size & Space")
            # Above-ground living area — the single most important size feature.
            gr_liv_area = st.number_input(
                "Above-Ground Living Area (sq ft)",
                min_value=334, max_value=5642, value=1442, step=50,
            )
            # First floor square footage.
            first_flr_sf = st.number_input(
                "1st Floor Area (sq ft)",
                min_value=334, max_value=5095, value=1084, step=50,
            )
            # Total basement square footage.
            total_bsmt_sf = st.number_input(
                "Total Basement Area (sq ft)",
                min_value=0, max_value=6110, value=990, step=50,
            )
            # Number of full bathrooms above ground.
            full_bath = st.selectbox("Full Bathrooms (above grade)", [0, 1, 2, 3, 4], index=2)
            # Number of bedrooms above basement level.
            bedroom = st.selectbox("Bedrooms (above grade)", [0, 1, 2, 3, 4, 5, 6, 7, 8], index=3)

        with col2:
            st.subheader("Quality & Age")
            # Overall quality rating 1–10 — the strongest single predictor of price.
            overall_qual = st.slider("Overall Quality (1=Poor, 10=Excellent)", 1, 10, 6)
            # Year the house was originally built.
            year_built = st.number_input("Year Built", min_value=1872, max_value=2010, value=1973, step=1)
            # Garage capacity in number of cars.
            garage_cars = st.selectbox("Garage Capacity (cars)", [0, 1, 2, 3, 4, 5], index=2)
            # Garage area in square feet.
            garage_area = st.number_input("Garage Area (sq ft)", min_value=0, max_value=1488, value=480, step=20)

        # Neighborhood selector — shown full-width below the two columns.
        st.subheader("Location")
        neighborhood_label = st.selectbox(
            "Neighborhood",
            options=list(NEIGHBORHOOD_OPTIONS.keys()),
            index=0,   # default to NAmes
        )

        # The Submit button — prediction only runs when this is clicked.
        submitted = st.form_submit_button("Predict Sale Price", type="primary")

    # ---- PREDICTION LOGIC (runs only after form submit) ----
    if submitted:
        # Start with a fresh copy of all defaults (213 features at median values).
        features = dict(DEFAULTS)

        # Override the defaults with what the user actually typed/selected.
        features["Gr_Liv_Area"] = float(gr_liv_area)
        features["First_Flr_SF"] = float(first_flr_sf)
        features["Total_Bsmt_SF"] = float(total_bsmt_sf)
        features["Full_Bath"] = float(full_bath)
        features["Bedroom_AbvGr"] = float(bedroom)
        features["Overall_Qual"] = float(overall_qual)
        features["Year_Built"] = float(year_built)
        features["Garage_Cars"] = float(garage_cars)
        features["Garage_Area"] = float(garage_area)

        # Handle the neighborhood: set all neighborhood flags to 0, then set the chosen one to 1.
        # This matches how one-hot encoding works in the trained model.
        for field in NEIGHBORHOOD_OPTIONS.values():
            features[field] = 0.0
        chosen_neighborhood_field = NEIGHBORHOOD_OPTIONS[neighborhood_label]
        features[chosen_neighborhood_field] = 1.0

        # Show a spinner while waiting for the API response.
        with st.spinner("Calling prediction API..."):
            try:
                # POST the full 213-feature dict to the FastAPI /predict endpoint.
                result = predict(features)

                # Extract the predicted dollar price from the response.
                price = result.get("predicted_price_dollars", 0)

                # Display the result prominently.
                st.success(f"**Predicted Sale Price: ${price:,.0f}**")

                # Show the metadata in a smaller info box below the price.
                st.info(
                    f"Model: {result.get('model_name')} "
                    f"v{result.get('model_version')} "
                    f"({result.get('model_alias')})"
                )

                # Show the raw log-scale prediction for learning purposes.
                with st.expander("Technical details"):
                    st.json(result)

            except Exception as e:
                # If the API call failed, show a clear error message.
                st.error(f"Prediction failed: {e}")
                st.info("Make sure the FastAPI server is running at localhost:8000.")
