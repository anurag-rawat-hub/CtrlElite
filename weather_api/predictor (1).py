import joblib
import os
import pandas as pd

# Load the model once at startup (not on every request)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "irrigation_prediction_v2.joblib")

try:
    with open(MODEL_PATH, "rb") as f:
        model = joblib.load(f)
    print(f"✅ Model loaded from {MODEL_PATH}")
except FileNotFoundError:
    model = None
    print(f"⚠️  Model file not found at {MODEL_PATH}. Prediction will fail at runtime.")


# The exact feature order the model was trained on
FEATURE_ORDER = [
    "Soil_Moisture",
    "Temperature_C",
    "Humidity",
    "Rainfall_mm",
    "Wind_Speed_kmh",
    "Rabi",
    "Zaid",
    "Harvest",
    "Sowing",
    "Vegetative",
    "Maize",
    "Potato",
    "Rice",
    "Sugarcane",
    "Wheat",
]

LABEL_MAP = {0: "Low", 1: "Medium", 2: "High"}


def get_irrigation_advice(input_data: dict) -> str:
    """
    Run the irrigation prediction model.

    Args:
        input_data: dict with all 15 feature keys (matches FEATURE_ORDER).

    Returns:
        Irrigation level as a string: "Low", "Medium", or "High".
    """
    if model is None:
        raise RuntimeError(
            f"Model not loaded. Ensure the .joblib file exists at: {MODEL_PATH}"
        )

    df = pd.DataFrame([input_data], columns=FEATURE_ORDER)
    prediction = model.predict(df)[0]

    if isinstance(prediction, str):
        return prediction

    return LABEL_MAP.get(int(prediction), "Unknown")