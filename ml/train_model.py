import joblib
import os
import pandas as pd
import requests
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# ── 1. Load the ML model ──────────────────────────────────────
MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "backend", "api", "irrigation_prediction_v2.joblib"
)
try:
    with open(MODEL_PATH, "rb") as f:
        model = joblib.load(f)
except FileNotFoundError:
    print(f"⚠️ Model not found at {MODEL_PATH}")
    model = None


# ── 2. Pydantic Schemas (merged from models(1).py) ────────────
class IrrigationRequest(BaseModel):
    latitude: float = Field(..., description="Farm latitude")
    longitude: float = Field(..., description="Farm longitude")
    soil_moisture: float = Field(..., description="Soil moisture (%)")
    temperature_c: float = Field(..., description="Live Sensor Temp")
    humidity: float = Field(..., description="Live Sensor Humidity")
    
    season: Literal["Kharif", "Rabi", "Zaid"] = Field(..., description="Current agricultural season")
    growth_stage: Literal["Sowing", "Vegetative", "Flowering", "Harvest"] = Field(..., description="Crop stage")
    crop: Literal["Maize", "Potato", "Rice", "Sugarcane", "Wheat"] = Field(..., description="Crop type")

class IrrigationResponse(BaseModel):
    irrigation_level: str = Field(..., description="Predicted level: Low / Medium / High")
    weather_used: dict = Field(..., description="Live weather data fetched from Google API")
    model_input: dict = Field(..., description="Full 15-feature vector passed to the model")

# ── 3. Weather Fetching Logic ─────────────────────────────────
def get_current_weather(lat: float, lng: float):
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    default_weather = {
        "Rainfall_mm": 0.0,
        "Wind_Speed_kmh": 12.5,
    }
    if not GOOGLE_API_KEY:
        return default_weather
        
    try:
        url = "https://weather.googleapis.com/v1/currentConditions:lookup"
        resp = requests.get(url, params={
            "key": GOOGLE_API_KEY,
            "location.latitude": lat,
            "location.longitude": lng,
            "unitsSystem": "METRIC",
        }, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            wind_speed = ((data.get("wind") or {}).get("speed") or {}).get("value", 12.5)
            rainfall = ((data.get("precipitation") or {}).get("qpf") or {}).get("quantity", 0.0)
            return {"Rainfall_mm": float(rainfall), "Wind_Speed_kmh": float(wind_speed)}
    except Exception as e:
        pass
    return default_weather

# ── 4. Main Inference Function ────────────────────────────────
def get_irrigation_advice(req: IrrigationRequest) -> IrrigationResponse:
    weather = get_current_weather(req.latitude, req.longitude)
    
    # Map back to 15 features
    input_data = {
        "Soil_Moisture": req.soil_moisture,
        "Temperature_C": req.temperature_c,
        "Humidity": req.humidity,
        "Rainfall_mm": weather["Rainfall_mm"],
        "Wind_Speed_kmh": weather["Wind_Speed_kmh"],
        "Rabi": int(req.season == "Rabi"),
        "Zaid": int(req.season == "Zaid"),
        "Harvest": int(req.growth_stage == "Harvest"),
        "Sowing": int(req.growth_stage == "Sowing"),
        "Vegetative": int(req.growth_stage == "Vegetative"),
        "Maize": int(req.crop == "Maize"),
        "Potato": int(req.crop == "Potato"),
        "Rice": int(req.crop == "Rice"),
        "Sugarcane": int(req.crop == "Sugarcane"),
        "Wheat": int(req.crop == "Wheat"),
    }
    
    df_input = pd.DataFrame([input_data])
    prediction = model.predict(df_input)[0] if model else 1
    
    if not isinstance(prediction, str):
        mapping = {0: "Low", 1: "Medium", 2: "High"}
        predicted_label = mapping.get(prediction, "Unknown")
    else:
        predicted_label = prediction
        
    return IrrigationResponse(
        irrigation_level=predicted_label,
        weather_used=weather,
        model_input=input_data
    )

# ── 5. Standalone Execution (Replace Sample Inputs) ───────────
if __name__ == "__main__":
    print("Fetching ACTUAL sensor readings from Django backend...")
    actual_soil, actual_temp, actual_hum = 25.0, 30.0, 50.0  # Fallbacks
    try:
        res = requests.get("http://127.0.0.1:8000/api/latest/", timeout=3)
        if res.status_code == 200:
            data = res.json()
            actual_soil = float(data.get("soil_moisture", 25.0))
            actual_temp = float(data.get("temperature", 30.0))
            actual_hum = float(data.get("humidity", 50.0))
            print(f"✓ Success! Real Sensor Data: Soil {actual_soil}%, Temp {actual_temp}°C, Hum {actual_hum}%")
    except requests.exceptions.RequestException:
        print("✗ Django server unreachable. Using fallback dummy sensor numbers.")
        
    print("\nBuilding Pydantic Request & Fetching Live Google Weather...")
    request_data = IrrigationRequest(
        latitude=19.0760,   # Mumbai India
        longitude=72.8777,
        soil_moisture=actual_soil,
        temperature_c=actual_temp,
        humidity=actual_hum,
        season="Zaid",
        growth_stage="Vegetative",
        crop="Rice"
    )
    
    response = get_irrigation_advice(request_data)
    print("\n------------------------------")
    print(f"💧 RECOMMENDED IRRIGATION: {response.irrigation_level}")
    print(f"☁️ WEATHER USED: {response.weather_used}")
    print(f"⚙️ FULL 15-FEATURE MATRIX: \n{response.model_input}")
    print("------------------------------\n")
