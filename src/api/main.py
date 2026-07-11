"""
Group 8 — API Layer (FastAPI)
Exposes the trained XGBoost model and system info via a REST API.
Endpoints: POST /predict, GET /health, GET /app-info/model,
           GET /app-info/experiment/{model_name},
           GET /app-info/pipeline/{deployment_name},
           GET /app-info/runs/{deployment_name}
"""

# --- Standard library ---
import os                          # for building file paths
from contextlib import asynccontextmanager  # for startup/shutdown lifecycle

# --- Third-party ---
import numpy as np                 # for exp() to reverse log-transformation
import pandas as pd                # for building the DataFrame the model expects
import httpx                       # for making HTTP calls to the Prefect REST API
import mlflow                      # for loading the registered model
from mlflow import MlflowClient    # for querying the MLflow Model Registry

# --- FastAPI ---
from fastapi import FastAPI, HTTPException   # main framework + error responses
from pydantic import BaseModel              # for defining request/response schemas
from typing import Optional, Any            # for optional fields in the input schema

# ==============================================================================
# TASK 8.1 — Pydantic request / response schemas
# ==============================================================================

# Build an absolute path to the project root so the SQLite DB is always found
# regardless of which directory uvicorn is started from.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# The MLflow tracking URI pointing to our local SQLite database file.
MLFLOW_TRACKING_URI = f"sqlite:///{PROJECT_ROOT}/mlruns.db"

# The name under which the best model is registered in the MLflow Model Registry.
MODEL_NAME = "AmesPricePredictor"

# The MLflow experiment name used during training (set in train_mlflow.py).
EXPERIMENT_NAME = "ames-housing-price-prediction"

# The alias that marks the production-ready version of the model.
MODEL_ALIAS = "production"

# The full MLflow URI used to load the model — alias-based loading.
MODEL_URI = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"

# The base URL for the locally running Prefect server REST API.
PREFECT_API_URL = "http://127.0.0.1:4200/api"


# --- 8.1a: Request schema — one field per encoded feature (213 total) ---
# All fields are Optional[float] with a default of 0.0.
# This means a caller can send any subset of features; missing ones default to zero.
class PredictRequest(BaseModel):
    # Numeric / ordinal features (55 fields)
    MS_SubClass: Optional[float] = 0.0           # type of dwelling (e.g. 20 = 1-story 1946+)
    Lot_Frontage: Optional[float] = 0.0          # linear feet of street connected to property
    Lot_Area: Optional[float] = 0.0              # lot size in square feet
    Lot_Shape: Optional[float] = 0.0             # general shape of property (encoded)
    Land_Slope: Optional[float] = 0.0            # slope of property (encoded)
    Overall_Qual: Optional[float] = 0.0          # overall material and finish quality (1-10)
    Overall_Cond: Optional[float] = 0.0          # overall condition rating (1-10)
    Year_Built: Optional[float] = 0.0            # original construction year
    Year_Remod_Add: Optional[float] = 0.0        # remodel year (same as Year_Built if no remodel)
    Mas_Vnr_Area: Optional[float] = 0.0          # masonry veneer area in square feet
    Exter_Qual: Optional[float] = 0.0            # exterior material quality (encoded)
    Exter_Cond: Optional[float] = 0.0            # exterior material condition (encoded)
    Bsmt_Qual: Optional[float] = 0.0             # basement height quality (encoded)
    Bsmt_Cond: Optional[float] = 0.0             # basement general condition (encoded)
    Bsmt_Exposure: Optional[float] = 0.0         # walkout/garden-level basement walls (encoded)
    BsmtFin_Type_1: Optional[float] = 0.0        # quality of primary basement finished area
    BsmtFin_SF_1: Optional[float] = 0.0          # type 1 finished square feet
    BsmtFin_Type_2: Optional[float] = 0.0        # quality of second finished area
    BsmtFin_SF_2: Optional[float] = 0.0          # type 2 finished square feet
    Bsmt_Unf_SF: Optional[float] = 0.0           # unfinished square feet of basement area
    Total_Bsmt_SF: Optional[float] = 0.0         # total square feet of basement area
    Heating_QC: Optional[float] = 0.0            # heating quality and condition (encoded)
    First_Flr_SF: Optional[float] = 0.0          # first floor square feet
    Second_Flr_SF: Optional[float] = 0.0         # second floor square feet
    Low_Qual_Fin_SF: Optional[float] = 0.0       # low quality finished square feet (all floors)
    Gr_Liv_Area: Optional[float] = 0.0           # above grade (ground) living area sq ft
    Bsmt_Full_Bath: Optional[float] = 0.0        # basement full bathrooms
    Bsmt_Half_Bath: Optional[float] = 0.0        # basement half bathrooms
    Full_Bath: Optional[float] = 0.0             # full bathrooms above grade
    Half_Bath: Optional[float] = 0.0             # half baths above grade
    Bedroom_AbvGr: Optional[float] = 0.0         # bedrooms above basement level
    Kitchen_AbvGr: Optional[float] = 0.0         # kitchens above grade
    Kitchen_Qual: Optional[float] = 0.0          # kitchen quality (encoded)
    TotRms_AbvGrd: Optional[float] = 0.0         # total rooms above grade (not bathrooms)
    Functional: Optional[float] = 0.0            # home functionality rating (encoded)
    Fireplaces: Optional[float] = 0.0            # number of fireplaces
    Fireplace_Qu: Optional[float] = 0.0          # fireplace quality (encoded)
    Garage_Yr_Blt: Optional[float] = 0.0         # year garage was built
    Garage_Finish: Optional[float] = 0.0         # interior finish of the garage (encoded)
    Garage_Cars: Optional[float] = 0.0           # size of garage in car capacity
    Garage_Area: Optional[float] = 0.0           # size of garage in square feet
    Garage_Qual: Optional[float] = 0.0           # garage quality (encoded)
    Garage_Cond: Optional[float] = 0.0           # garage condition (encoded)
    Paved_Drive: Optional[float] = 0.0           # paved driveway (encoded)
    Wood_Deck_SF: Optional[float] = 0.0          # wood deck area in square feet
    Open_Porch_SF: Optional[float] = 0.0         # open porch area in square feet
    Enclosed_Porch: Optional[float] = 0.0        # enclosed porch area in square feet
    Three_Ssn_Porch: Optional[float] = 0.0       # three season porch area in square feet
    Screen_Porch: Optional[float] = 0.0          # screen porch area in square feet
    Pool_Area: Optional[float] = 0.0             # pool area in square feet
    Pool_QC: Optional[float] = 0.0               # pool quality (encoded)
    Fence: Optional[float] = 0.0                 # fence quality (encoded)
    Misc_Val: Optional[float] = 0.0              # value of miscellaneous feature
    Mo_Sold: Optional[float] = 0.0               # month sold
    Yr_Sold: Optional[float] = 0.0               # year sold

    # One-hot encoded categorical features (158 binary fields)
    MS_Zoning_C_all: Optional[float] = 0.0
    MS_Zoning_FV: Optional[float] = 0.0
    MS_Zoning_I_all: Optional[float] = 0.0
    MS_Zoning_RH: Optional[float] = 0.0
    MS_Zoning_RL: Optional[float] = 0.0
    MS_Zoning_RM: Optional[float] = 0.0
    Street_Pave: Optional[float] = 0.0
    Alley_None: Optional[float] = 0.0
    Alley_Pave: Optional[float] = 0.0
    Land_Contour_HLS: Optional[float] = 0.0
    Land_Contour_Low: Optional[float] = 0.0
    Land_Contour_Lvl: Optional[float] = 0.0
    Utilities_NoSeWa: Optional[float] = 0.0
    Utilities_NoSewr: Optional[float] = 0.0
    Lot_Config_CulDSac: Optional[float] = 0.0
    Lot_Config_FR2: Optional[float] = 0.0
    Lot_Config_FR3: Optional[float] = 0.0
    Lot_Config_Inside: Optional[float] = 0.0
    Neighborhood_Blueste: Optional[float] = 0.0
    Neighborhood_BrDale: Optional[float] = 0.0
    Neighborhood_BrkSide: Optional[float] = 0.0
    Neighborhood_ClearCr: Optional[float] = 0.0
    Neighborhood_CollgCr: Optional[float] = 0.0
    Neighborhood_Crawfor: Optional[float] = 0.0
    Neighborhood_Edwards: Optional[float] = 0.0
    Neighborhood_Gilbert: Optional[float] = 0.0
    Neighborhood_Greens: Optional[float] = 0.0
    Neighborhood_GrnHill: Optional[float] = 0.0
    Neighborhood_IDOTRR: Optional[float] = 0.0
    Neighborhood_Landmrk: Optional[float] = 0.0
    Neighborhood_MeadowV: Optional[float] = 0.0
    Neighborhood_Mitchel: Optional[float] = 0.0
    Neighborhood_NAmes: Optional[float] = 0.0
    Neighborhood_NPkVill: Optional[float] = 0.0
    Neighborhood_NWAmes: Optional[float] = 0.0
    Neighborhood_NoRidge: Optional[float] = 0.0
    Neighborhood_NridgHt: Optional[float] = 0.0
    Neighborhood_OldTown: Optional[float] = 0.0
    Neighborhood_SWISU: Optional[float] = 0.0
    Neighborhood_Sawyer: Optional[float] = 0.0
    Neighborhood_SawyerW: Optional[float] = 0.0
    Neighborhood_Somerst: Optional[float] = 0.0
    Neighborhood_StoneBr: Optional[float] = 0.0
    Neighborhood_Timber: Optional[float] = 0.0
    Neighborhood_Veenker: Optional[float] = 0.0
    Condition_1_Feedr: Optional[float] = 0.0
    Condition_1_Norm: Optional[float] = 0.0
    Condition_1_PosA: Optional[float] = 0.0
    Condition_1_PosN: Optional[float] = 0.0
    Condition_1_RRAe: Optional[float] = 0.0
    Condition_1_RRAn: Optional[float] = 0.0
    Condition_1_RRNe: Optional[float] = 0.0
    Condition_1_RRNn: Optional[float] = 0.0
    Condition_2_Feedr: Optional[float] = 0.0
    Condition_2_Norm: Optional[float] = 0.0
    Condition_2_PosA: Optional[float] = 0.0
    Condition_2_PosN: Optional[float] = 0.0
    Condition_2_RRAe: Optional[float] = 0.0
    Condition_2_RRAn: Optional[float] = 0.0
    Condition_2_RRNn: Optional[float] = 0.0
    Bldg_Type_2fmCon: Optional[float] = 0.0
    Bldg_Type_Duplex: Optional[float] = 0.0
    Bldg_Type_Twnhs: Optional[float] = 0.0
    Bldg_Type_TwnhsE: Optional[float] = 0.0
    House_Style_1_5Unf: Optional[float] = 0.0
    House_Style_1Story: Optional[float] = 0.0
    House_Style_2_5Fin: Optional[float] = 0.0
    House_Style_2_5Unf: Optional[float] = 0.0
    House_Style_2Story: Optional[float] = 0.0
    House_Style_SFoyer: Optional[float] = 0.0
    House_Style_SLvl: Optional[float] = 0.0
    Roof_Style_Gable: Optional[float] = 0.0
    Roof_Style_Gambrel: Optional[float] = 0.0
    Roof_Style_Hip: Optional[float] = 0.0
    Roof_Style_Mansard: Optional[float] = 0.0
    Roof_Style_Shed: Optional[float] = 0.0
    Roof_Matl_CompShg: Optional[float] = 0.0
    Roof_Matl_Membran: Optional[float] = 0.0
    Roof_Matl_Metal: Optional[float] = 0.0
    Roof_Matl_Roll: Optional[float] = 0.0
    Roof_Matl_TarGrv: Optional[float] = 0.0
    Roof_Matl_WdShake: Optional[float] = 0.0
    Roof_Matl_WdShngl: Optional[float] = 0.0
    Exterior_1st_AsphShn: Optional[float] = 0.0
    Exterior_1st_BrkComm: Optional[float] = 0.0
    Exterior_1st_BrkFace: Optional[float] = 0.0
    Exterior_1st_CBlock: Optional[float] = 0.0
    Exterior_1st_CemntBd: Optional[float] = 0.0
    Exterior_1st_HdBoard: Optional[float] = 0.0
    Exterior_1st_ImStucc: Optional[float] = 0.0
    Exterior_1st_MetalSd: Optional[float] = 0.0
    Exterior_1st_Plywood: Optional[float] = 0.0
    Exterior_1st_PreCast: Optional[float] = 0.0
    Exterior_1st_Stone: Optional[float] = 0.0
    Exterior_1st_Stucco: Optional[float] = 0.0
    Exterior_1st_VinylSd: Optional[float] = 0.0
    Exterior_1st_WdSdng: Optional[float] = 0.0
    Exterior_1st_WdShing: Optional[float] = 0.0
    Exterior_2nd_AsphShn: Optional[float] = 0.0
    Exterior_2nd_BrkCmn: Optional[float] = 0.0
    Exterior_2nd_BrkFace: Optional[float] = 0.0
    Exterior_2nd_CBlock: Optional[float] = 0.0
    Exterior_2nd_CmentBd: Optional[float] = 0.0
    Exterior_2nd_HdBoard: Optional[float] = 0.0
    Exterior_2nd_ImStucc: Optional[float] = 0.0
    Exterior_2nd_MetalSd: Optional[float] = 0.0
    Exterior_2nd_Other: Optional[float] = 0.0
    Exterior_2nd_Plywood: Optional[float] = 0.0
    Exterior_2nd_PreCast: Optional[float] = 0.0
    Exterior_2nd_Stone: Optional[float] = 0.0
    Exterior_2nd_Stucco: Optional[float] = 0.0
    Exterior_2nd_VinylSd: Optional[float] = 0.0
    Exterior_2nd_WdSdng: Optional[float] = 0.0
    Exterior_2nd_WdShng: Optional[float] = 0.0
    Mas_Vnr_Type_BrkFace: Optional[float] = 0.0
    Mas_Vnr_Type_CBlock: Optional[float] = 0.0
    Mas_Vnr_Type_None: Optional[float] = 0.0
    Mas_Vnr_Type_Stone: Optional[float] = 0.0
    Foundation_CBlock: Optional[float] = 0.0
    Foundation_PConc: Optional[float] = 0.0
    Foundation_Slab: Optional[float] = 0.0
    Foundation_Stone: Optional[float] = 0.0
    Foundation_Wood: Optional[float] = 0.0
    Heating_GasA: Optional[float] = 0.0
    Heating_GasW: Optional[float] = 0.0
    Heating_Grav: Optional[float] = 0.0
    Heating_OthW: Optional[float] = 0.0
    Heating_Wall: Optional[float] = 0.0
    Central_Air_Y: Optional[float] = 0.0
    Electrical_FuseF: Optional[float] = 0.0
    Electrical_FuseP: Optional[float] = 0.0
    Electrical_Mix: Optional[float] = 0.0
    Electrical_SBrkr: Optional[float] = 0.0
    Garage_Type_Attchd: Optional[float] = 0.0
    Garage_Type_Basment: Optional[float] = 0.0
    Garage_Type_BuiltIn: Optional[float] = 0.0
    Garage_Type_CarPort: Optional[float] = 0.0
    Garage_Type_Detchd: Optional[float] = 0.0
    Garage_Type_None: Optional[float] = 0.0
    Misc_Feature_Gar2: Optional[float] = 0.0
    Misc_Feature_None: Optional[float] = 0.0
    Misc_Feature_Othr: Optional[float] = 0.0
    Misc_Feature_Shed: Optional[float] = 0.0
    Misc_Feature_TenC: Optional[float] = 0.0
    Sale_Type_CWD: Optional[float] = 0.0
    Sale_Type_Con: Optional[float] = 0.0
    Sale_Type_ConLD: Optional[float] = 0.0
    Sale_Type_ConLI: Optional[float] = 0.0
    Sale_Type_ConLw: Optional[float] = 0.0
    Sale_Type_New: Optional[float] = 0.0
    Sale_Type_Oth: Optional[float] = 0.0
    Sale_Type_VWD: Optional[float] = 0.0
    Sale_Type_WD: Optional[float] = 0.0
    Sale_Condition_AdjLand: Optional[float] = 0.0
    Sale_Condition_Alloca: Optional[float] = 0.0
    Sale_Condition_Family: Optional[float] = 0.0
    Sale_Condition_Normal: Optional[float] = 0.0
    Sale_Condition_Partial: Optional[float] = 0.0


# Mapping from Pydantic field names (underscores) to the original dataset column names
# (which have spaces, slashes, and special characters the model was trained on).
FIELD_TO_COLUMN = {
    "MS_SubClass": "MS SubClass",
    "Lot_Frontage": "Lot Frontage",
    "Lot_Area": "Lot Area",
    "Lot_Shape": "Lot Shape",
    "Land_Slope": "Land Slope",
    "Overall_Qual": "Overall Qual",
    "Overall_Cond": "Overall Cond",
    "Year_Built": "Year Built",
    "Year_Remod_Add": "Year Remod/Add",
    "Mas_Vnr_Area": "Mas Vnr Area",
    "Exter_Qual": "Exter Qual",
    "Exter_Cond": "Exter Cond",
    "Bsmt_Qual": "Bsmt Qual",
    "Bsmt_Cond": "Bsmt Cond",
    "Bsmt_Exposure": "Bsmt Exposure",
    "BsmtFin_Type_1": "BsmtFin Type 1",
    "BsmtFin_SF_1": "BsmtFin SF 1",
    "BsmtFin_Type_2": "BsmtFin Type 2",
    "BsmtFin_SF_2": "BsmtFin SF 2",
    "Bsmt_Unf_SF": "Bsmt Unf SF",
    "Total_Bsmt_SF": "Total Bsmt SF",
    "Heating_QC": "Heating QC",
    "First_Flr_SF": "1st Flr SF",
    "Second_Flr_SF": "2nd Flr SF",
    "Low_Qual_Fin_SF": "Low Qual Fin SF",
    "Gr_Liv_Area": "Gr Liv Area",
    "Bsmt_Full_Bath": "Bsmt Full Bath",
    "Bsmt_Half_Bath": "Bsmt Half Bath",
    "Full_Bath": "Full Bath",
    "Half_Bath": "Half Bath",
    "Bedroom_AbvGr": "Bedroom AbvGr",
    "Kitchen_AbvGr": "Kitchen AbvGr",
    "Kitchen_Qual": "Kitchen Qual",
    "TotRms_AbvGrd": "TotRms AbvGrd",
    "Functional": "Functional",
    "Fireplaces": "Fireplaces",
    "Fireplace_Qu": "Fireplace Qu",
    "Garage_Yr_Blt": "Garage Yr Blt",
    "Garage_Finish": "Garage Finish",
    "Garage_Cars": "Garage Cars",
    "Garage_Area": "Garage Area",
    "Garage_Qual": "Garage Qual",
    "Garage_Cond": "Garage Cond",
    "Paved_Drive": "Paved Drive",
    "Wood_Deck_SF": "Wood Deck SF",
    "Open_Porch_SF": "Open Porch SF",
    "Enclosed_Porch": "Enclosed Porch",
    "Three_Ssn_Porch": "3Ssn Porch",
    "Screen_Porch": "Screen Porch",
    "Pool_Area": "Pool Area",
    "Pool_QC": "Pool QC",
    "Fence": "Fence",
    "Misc_Val": "Misc Val",
    "Mo_Sold": "Mo Sold",
    "Yr_Sold": "Yr Sold",
    "MS_Zoning_C_all": "MS Zoning_C (all)",
    "MS_Zoning_FV": "MS Zoning_FV",
    "MS_Zoning_I_all": "MS Zoning_I (all)",
    "MS_Zoning_RH": "MS Zoning_RH",
    "MS_Zoning_RL": "MS Zoning_RL",
    "MS_Zoning_RM": "MS Zoning_RM",
    "Street_Pave": "Street_Pave",
    "Alley_None": "Alley_None",
    "Alley_Pave": "Alley_Pave",
    "Land_Contour_HLS": "Land Contour_HLS",
    "Land_Contour_Low": "Land Contour_Low",
    "Land_Contour_Lvl": "Land Contour_Lvl",
    "Utilities_NoSeWa": "Utilities_NoSeWa",
    "Utilities_NoSewr": "Utilities_NoSewr",
    "Lot_Config_CulDSac": "Lot Config_CulDSac",
    "Lot_Config_FR2": "Lot Config_FR2",
    "Lot_Config_FR3": "Lot Config_FR3",
    "Lot_Config_Inside": "Lot Config_Inside",
    "Neighborhood_Blueste": "Neighborhood_Blueste",
    "Neighborhood_BrDale": "Neighborhood_BrDale",
    "Neighborhood_BrkSide": "Neighborhood_BrkSide",
    "Neighborhood_ClearCr": "Neighborhood_ClearCr",
    "Neighborhood_CollgCr": "Neighborhood_CollgCr",
    "Neighborhood_Crawfor": "Neighborhood_Crawfor",
    "Neighborhood_Edwards": "Neighborhood_Edwards",
    "Neighborhood_Gilbert": "Neighborhood_Gilbert",
    "Neighborhood_Greens": "Neighborhood_Greens",
    "Neighborhood_GrnHill": "Neighborhood_GrnHill",
    "Neighborhood_IDOTRR": "Neighborhood_IDOTRR",
    "Neighborhood_Landmrk": "Neighborhood_Landmrk",
    "Neighborhood_MeadowV": "Neighborhood_MeadowV",
    "Neighborhood_Mitchel": "Neighborhood_Mitchel",
    "Neighborhood_NAmes": "Neighborhood_NAmes",
    "Neighborhood_NPkVill": "Neighborhood_NPkVill",
    "Neighborhood_NWAmes": "Neighborhood_NWAmes",
    "Neighborhood_NoRidge": "Neighborhood_NoRidge",
    "Neighborhood_NridgHt": "Neighborhood_NridgHt",
    "Neighborhood_OldTown": "Neighborhood_OldTown",
    "Neighborhood_SWISU": "Neighborhood_SWISU",
    "Neighborhood_Sawyer": "Neighborhood_Sawyer",
    "Neighborhood_SawyerW": "Neighborhood_SawyerW",
    "Neighborhood_Somerst": "Neighborhood_Somerst",
    "Neighborhood_StoneBr": "Neighborhood_StoneBr",
    "Neighborhood_Timber": "Neighborhood_Timber",
    "Neighborhood_Veenker": "Neighborhood_Veenker",
    "Condition_1_Feedr": "Condition 1_Feedr",
    "Condition_1_Norm": "Condition 1_Norm",
    "Condition_1_PosA": "Condition 1_PosA",
    "Condition_1_PosN": "Condition 1_PosN",
    "Condition_1_RRAe": "Condition 1_RRAe",
    "Condition_1_RRAn": "Condition 1_RRAn",
    "Condition_1_RRNe": "Condition 1_RRNe",
    "Condition_1_RRNn": "Condition 1_RRNn",
    "Condition_2_Feedr": "Condition 2_Feedr",
    "Condition_2_Norm": "Condition 2_Norm",
    "Condition_2_PosA": "Condition 2_PosA",
    "Condition_2_PosN": "Condition 2_PosN",
    "Condition_2_RRAe": "Condition 2_RRAe",
    "Condition_2_RRAn": "Condition 2_RRAn",
    "Condition_2_RRNn": "Condition 2_RRNn",
    "Bldg_Type_2fmCon": "Bldg Type_2fmCon",
    "Bldg_Type_Duplex": "Bldg Type_Duplex",
    "Bldg_Type_Twnhs": "Bldg Type_Twnhs",
    "Bldg_Type_TwnhsE": "Bldg Type_TwnhsE",
    "House_Style_1_5Unf": "House Style_1.5Unf",
    "House_Style_1Story": "House Style_1Story",
    "House_Style_2_5Fin": "House Style_2.5Fin",
    "House_Style_2_5Unf": "House Style_2.5Unf",
    "House_Style_2Story": "House Style_2Story",
    "House_Style_SFoyer": "House Style_SFoyer",
    "House_Style_SLvl": "House Style_SLvl",
    "Roof_Style_Gable": "Roof Style_Gable",
    "Roof_Style_Gambrel": "Roof Style_Gambrel",
    "Roof_Style_Hip": "Roof Style_Hip",
    "Roof_Style_Mansard": "Roof Style_Mansard",
    "Roof_Style_Shed": "Roof Style_Shed",
    "Roof_Matl_CompShg": "Roof Matl_CompShg",
    "Roof_Matl_Membran": "Roof Matl_Membran",
    "Roof_Matl_Metal": "Roof Matl_Metal",
    "Roof_Matl_Roll": "Roof Matl_Roll",
    "Roof_Matl_TarGrv": "Roof Matl_Tar&Grv",
    "Roof_Matl_WdShake": "Roof Matl_WdShake",
    "Roof_Matl_WdShngl": "Roof Matl_WdShngl",
    "Exterior_1st_AsphShn": "Exterior 1st_AsphShn",
    "Exterior_1st_BrkComm": "Exterior 1st_BrkComm",
    "Exterior_1st_BrkFace": "Exterior 1st_BrkFace",
    "Exterior_1st_CBlock": "Exterior 1st_CBlock",
    "Exterior_1st_CemntBd": "Exterior 1st_CemntBd",
    "Exterior_1st_HdBoard": "Exterior 1st_HdBoard",
    "Exterior_1st_ImStucc": "Exterior 1st_ImStucc",
    "Exterior_1st_MetalSd": "Exterior 1st_MetalSd",
    "Exterior_1st_Plywood": "Exterior 1st_Plywood",
    "Exterior_1st_PreCast": "Exterior 1st_PreCast",
    "Exterior_1st_Stone": "Exterior 1st_Stone",
    "Exterior_1st_Stucco": "Exterior 1st_Stucco",
    "Exterior_1st_VinylSd": "Exterior 1st_VinylSd",
    "Exterior_1st_WdSdng": "Exterior 1st_Wd Sdng",
    "Exterior_1st_WdShing": "Exterior 1st_WdShing",
    "Exterior_2nd_AsphShn": "Exterior 2nd_AsphShn",
    "Exterior_2nd_BrkCmn": "Exterior 2nd_Brk Cmn",
    "Exterior_2nd_BrkFace": "Exterior 2nd_BrkFace",
    "Exterior_2nd_CBlock": "Exterior 2nd_CBlock",
    "Exterior_2nd_CmentBd": "Exterior 2nd_CmentBd",
    "Exterior_2nd_HdBoard": "Exterior 2nd_HdBoard",
    "Exterior_2nd_ImStucc": "Exterior 2nd_ImStucc",
    "Exterior_2nd_MetalSd": "Exterior 2nd_MetalSd",
    "Exterior_2nd_Other": "Exterior 2nd_Other",
    "Exterior_2nd_Plywood": "Exterior 2nd_Plywood",
    "Exterior_2nd_PreCast": "Exterior 2nd_PreCast",
    "Exterior_2nd_Stone": "Exterior 2nd_Stone",
    "Exterior_2nd_Stucco": "Exterior 2nd_Stucco",
    "Exterior_2nd_VinylSd": "Exterior 2nd_VinylSd",
    "Exterior_2nd_WdSdng": "Exterior 2nd_Wd Sdng",
    "Exterior_2nd_WdShng": "Exterior 2nd_Wd Shng",
    "Mas_Vnr_Type_BrkFace": "Mas Vnr Type_BrkFace",
    "Mas_Vnr_Type_CBlock": "Mas Vnr Type_CBlock",
    "Mas_Vnr_Type_None": "Mas Vnr Type_None",
    "Mas_Vnr_Type_Stone": "Mas Vnr Type_Stone",
    "Foundation_CBlock": "Foundation_CBlock",
    "Foundation_PConc": "Foundation_PConc",
    "Foundation_Slab": "Foundation_Slab",
    "Foundation_Stone": "Foundation_Stone",
    "Foundation_Wood": "Foundation_Wood",
    "Heating_GasA": "Heating_GasA",
    "Heating_GasW": "Heating_GasW",
    "Heating_Grav": "Heating_Grav",
    "Heating_OthW": "Heating_OthW",
    "Heating_Wall": "Heating_Wall",
    "Central_Air_Y": "Central Air_Y",
    "Electrical_FuseF": "Electrical_FuseF",
    "Electrical_FuseP": "Electrical_FuseP",
    "Electrical_Mix": "Electrical_Mix",
    "Electrical_SBrkr": "Electrical_SBrkr",
    "Garage_Type_Attchd": "Garage Type_Attchd",
    "Garage_Type_Basment": "Garage Type_Basment",
    "Garage_Type_BuiltIn": "Garage Type_BuiltIn",
    "Garage_Type_CarPort": "Garage Type_CarPort",
    "Garage_Type_Detchd": "Garage Type_Detchd",
    "Garage_Type_None": "Garage Type_None",
    "Misc_Feature_Gar2": "Misc Feature_Gar2",
    "Misc_Feature_None": "Misc Feature_None",
    "Misc_Feature_Othr": "Misc Feature_Othr",
    "Misc_Feature_Shed": "Misc Feature_Shed",
    "Misc_Feature_TenC": "Misc Feature_TenC",
    "Sale_Type_CWD": "Sale Type_CWD",
    "Sale_Type_Con": "Sale Type_Con",
    "Sale_Type_ConLD": "Sale Type_ConLD",
    "Sale_Type_ConLI": "Sale Type_ConLI",
    "Sale_Type_ConLw": "Sale Type_ConLw",
    "Sale_Type_New": "Sale Type_New",
    "Sale_Type_Oth": "Sale Type_Oth",
    "Sale_Type_VWD": "Sale Type_VWD",
    "Sale_Type_WD": "Sale Type_WD ",
    "Sale_Condition_AdjLand": "Sale Condition_AdjLand",
    "Sale_Condition_Alloca": "Sale Condition_Alloca",
    "Sale_Condition_Family": "Sale Condition_Family",
    "Sale_Condition_Normal": "Sale Condition_Normal",
    "Sale_Condition_Partial": "Sale Condition_Partial",
}


# --- 8.1b: Response schema for POST /predict ---
class PredictResponse(BaseModel):
    predicted_price_dollars: float   # final dollar price after reversing log transform
    log_prediction: float            # raw model output (log scale) — useful for debugging
    model_name: str                  # registered model name in MLflow
    model_version: str               # version number of the loaded model
    model_alias: str                 # alias used to load (e.g. "production")


# ==============================================================================
# TASK 8.2 — Lifespan: load model once at startup
# ==============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP: runs once before the app starts accepting requests ---

    # Tell MLflow which database file to read from.
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # Load the production model from the MLflow Model Registry.
    # This reads the model files from disk into memory — takes ~1-2 seconds once.
    print(f"Loading model from MLflow: {MODEL_URI}")
    app.state.model = mlflow.pyfunc.load_model(MODEL_URI)

    # Create a reusable MLflow client for querying the registry and experiments.
    app.state.mlflow_client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)

    # Look up and store the model version so we can include it in every response.
    mv = app.state.mlflow_client.get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
    # Store as string — Pydantic response model declares model_version as str.
    app.state.model_version = str(mv.version)

    print(f"Model loaded: {MODEL_NAME} version {mv.version} alias={MODEL_ALIAS}")

    # Hand control to the running app — everything above ran at startup.
    yield

    # --- SHUTDOWN: runs when the app is stopping (cleanup if needed) ---
    print("App shutting down.")


# ==============================================================================
# Create the FastAPI application with the lifespan handler attached.
# ==============================================================================
app = FastAPI(
    title="Ames House Price Predictor API",
    description="Predicts Ames Iowa house prices using an XGBoost model tracked in MLflow.",
    version="1.0.0",
    lifespan=lifespan,
)


# ==============================================================================
# TASK 8.2 — POST /predict
# ==============================================================================

@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    # Convert the incoming Pydantic model to a plain Python dictionary.
    raw = request.model_dump()

    # Rename fields from Pydantic names (underscores) back to original column names
    # (spaces, slashes, special chars) that the model was trained on.
    renamed = {FIELD_TO_COLUMN[k]: v for k, v in raw.items()}

    # Wrap the single row of values in a pandas DataFrame — the model expects this format.
    input_df = pd.DataFrame([renamed])

    # Reorder columns to exactly match the order the model was trained on.
    # XGBoost validates feature name order; mismatches cause a ValueError.
    model_col_order = app.state.model._model_impl.xgb_model.get_booster().feature_names
    input_df = input_df[model_col_order]

    # Run the model on the input row; result is an array of log-transformed predictions.
    log_pred = app.state.model.predict(input_df)[0]

    # Reverse the log transformation: the model outputs log(SalePrice), we want dollars.
    dollar_pred = float(np.exp(log_pred))

    # Return the prediction along with metadata about which model version was used.
    return PredictResponse(
        predicted_price_dollars=round(dollar_pred, 2),
        log_prediction=round(float(log_pred), 6),
        model_name=MODEL_NAME,
        model_version=app.state.model_version,
        model_alias=MODEL_ALIAS,
    )


# ==============================================================================
# TASK 8.3 — GET /health
# ==============================================================================

@app.get("/health")
def health():
    # Check 1: is the model object sitting in app.state (loaded at startup)?
    model_status = "loaded" if hasattr(app.state, "model") and app.state.model is not None else "not loaded"

    # Check 2: can we query the MLflow registry? (reads from the SQLite file)
    try:
        app.state.mlflow_client.get_registered_model(MODEL_NAME)
        mlflow_status = "ok"
    except Exception as e:
        mlflow_status = f"error: {str(e)}"

    # Check 3: can we reach the Prefect server? (HTTP ping to its health endpoint)
    try:
        resp = httpx.get(f"{PREFECT_API_URL}/health", timeout=3.0)
        prefect_status = "ok" if resp.status_code == 200 else f"error: HTTP {resp.status_code}"
    except Exception as e:
        prefect_status = f"error: {str(e)}"

    # Decide the overall status — "healthy" only if all three checks pass.
    overall = "healthy" if (model_status == "loaded" and mlflow_status == "ok" and prefect_status == "ok") else "degraded"

    # Always return 200 — health endpoint must never crash or return 5xx.
    return {
        "model": model_status,
        "mlflow": mlflow_status,
        "prefect": prefect_status,
        "overall": overall,
    }


# ==============================================================================
# TASK 8.4 — GET /app-info/model
# ==============================================================================

@app.get("/app-info/model")
def app_info_model():
    # Wrap in try/except — if MLflow is unreachable, return 503 (not a crash).
    try:
        # Get the registered model metadata from the MLflow registry.
        rm = app.state.mlflow_client.get_registered_model(MODEL_NAME)

        # Get the specific version that has the "production" alias.
        mv = app.state.mlflow_client.get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)

        # Return the key fields about this model.
        return {
            "name": rm.name,
            "version": mv.version,
            "alias": MODEL_ALIAS,
            "run_id": mv.run_id,
            "description": rm.description or "",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail={"service": "mlflow", "error": str(e)})


# ==============================================================================
# TASK 8.5 — GET /app-info/experiment/{model_name}
# ==============================================================================

# Map the model_name path parameter to the MLflow run tag that identifies each model.
# During training (train_mlflow.py), each run logs the model type as a tag.
MODEL_NAME_TO_TAG = {
    "ridge": "Ridge",
    "lasso": "Lasso",
    "xgboost": "XGBoost",
}

@app.get("/app-info/experiment/{model_name}")
def app_info_experiment(model_name: str):
    # Validate that the caller used a recognised model name.
    if model_name.lower() not in MODEL_NAME_TO_TAG:
        raise HTTPException(status_code=404, detail=f"Unknown model '{model_name}'. Use: ridge, lasso, xgboost")

    # Wrap in try/except — 503 if MLflow is unreachable.
    try:
        client = app.state.mlflow_client

        # Find the experiment by name (set during training in train_mlflow.py).
        experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
        if experiment is None:
            raise HTTPException(status_code=404, detail=f"MLflow experiment '{EXPERIMENT_NAME}' not found")

        # Search runs filtered by the model_type param (logged as a param, not a tag).
        param_value = MODEL_NAME_TO_TAG[model_name.lower()]
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"params.model_type = '{param_value}'",
            order_by=["start_time DESC"],
            max_results=1,
        )

        # If no run found for this model type, return a 404.
        if not runs:
            raise HTTPException(status_code=404, detail=f"No MLflow run found for model '{model_name}'")

        # Take the matching run and extract its metrics.
        run = runs[0]
        return {
            "model": model_name,
            "experiment_name": experiment.name,
            "experiment_id": experiment.experiment_id,
            "run_id": run.info.run_id,
            "run_status": run.info.status,
            "metrics": run.data.metrics,
        }
    except HTTPException:
        # Re-raise 404s as-is — don't wrap them in a 503.
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail={"service": "mlflow", "error": str(e)})


# ==============================================================================
# TASK 8.6 — GET /app-info/pipeline/{deployment_name}
# ==============================================================================

@app.get("/app-info/pipeline/{deployment_name}")
def app_info_pipeline(deployment_name: str):
    # Wrap in try/except — 503 if Prefect server is not running.
    try:
        # Call the Prefect REST API — listing deployments requires POST /deployments/filter.
        resp = httpx.post(
            f"{PREFECT_API_URL}/deployments/filter",
            json={"deployments": {"name": {"any_": [deployment_name]}}},
            timeout=5.0,
        )
        resp.raise_for_status()
        deployments = resp.json()

        # Pick the first matching deployment (filter already scoped to the name).
        match = deployments[0] if deployments else None

        # Return 404 if no deployment with that name exists.
        if match is None:
            raise HTTPException(status_code=404, detail=f"Deployment '{deployment_name}' not found in Prefect")

        # Resolve the flow name from the flow_id (Prefect stores flow_id, not flow_name).
        flow_id = match.get("flow_id")
        flow_name = flow_id  # fallback to UUID if lookup fails
        if flow_id:
            flow_resp = httpx.get(f"{PREFECT_API_URL}/flows/{flow_id}", timeout=5.0)
            if flow_resp.status_code == 200:
                flow_name = flow_resp.json().get("name", flow_id)

        # Extract and return the key deployment fields.
        return {
            "deployment_name": match.get("name"),
            "flow_name": flow_name,
            "schedule": match.get("schedules"),
            "status": match.get("status"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail={"service": "prefect", "error": str(e)})


# ==============================================================================
# TASK 8.7 — GET /app-info/runs/{deployment_name}
# ==============================================================================

@app.get("/app-info/runs/{deployment_name}")
def app_info_runs(deployment_name: str):
    # Wrap in try/except — 503 if Prefect server is not running.
    try:
        # Step 1: find the deployment by name using POST /deployments/filter.
        resp = httpx.post(
            f"{PREFECT_API_URL}/deployments/filter",
            json={"deployments": {"name": {"any_": [deployment_name]}}},
            timeout=5.0,
        )
        resp.raise_for_status()
        deployments = resp.json()
        match = deployments[0] if deployments else None
        if match is None:
            raise HTTPException(status_code=404, detail=f"Deployment '{deployment_name}' not found in Prefect")

        deployment_id = match["id"]

        # Step 2: query the flow-runs API, filtered by this deployment ID, newest first.
        runs_resp = httpx.post(
            f"{PREFECT_API_URL}/flow_runs/filter",
            json={
                "deployment_filter": {"id": {"any_": [deployment_id]}},
                "sort": "START_TIME_DESC",
                "limit": 10,
            },
            timeout=5.0,
        )
        runs_resp.raise_for_status()
        runs = runs_resp.json()

        # Format the run list — keep only the fields useful to display.
        formatted = [
            {
                "run_id": r.get("id"),
                "name": r.get("name"),
                "state": r.get("state", {}).get("type"),
                "start_time": r.get("start_time"),
                "end_time": r.get("end_time"),
                "total_run_time": r.get("total_run_time"),
            }
            for r in runs
        ]

        return {
            "deployment_name": deployment_name,
            "recent_runs": formatted,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail={"service": "prefect", "error": str(e)})
