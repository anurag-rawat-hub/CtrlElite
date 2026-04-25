from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv

from models import (
    IrrigationRequest,
    IrrigationResponse,
    CurrentConditionsResponse,
    HourlyForecastResponse,
    DailyForecastResponse,
    HistoryResponse,
)
from predictor import get_irrigation_advice

load_dotenv()

app = FastAPI(
    title="Smart Irrigation API",
    description=(
        "Combines Google Maps Weather API with an ML model "
        "to recommend irrigation levels based on real-time weather + crop data."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BASE_URL = "https://weather.googleapis.com/v1"


def get_api_key() -> str:
    if not GOOGLE_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY is not set in environment variables.",
        )
    return GOOGLE_API_KEY


async def fetch_weather(endpoint: str, params: dict) -> dict:
    """Generic helper to call Google Weather API endpoints."""
    params["key"] = get_api_key()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{BASE_URL}/{endpoint}", params=params)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.json().get("error", {}).get("message", "Google API error"),
        )
    return response.json()


async def get_current_weather_data(lat: float, lng: float) -> dict:
    """
    Fetch current weather and extract the 4 fields needed by the ML model:
      - Temperature_C
      - Humidity
      - Rainfall_mm
      - Wind_Speed_kmh
    """
    data = await fetch_weather(
        "currentConditions:lookup",
        {
            "location.latitude": lat,
            "location.longitude": lng,
            "unitsSystem": "METRIC",
        },
    )

    temperature  = (data.get("temperature") or {}).get("degrees", 0.0)
    humidity     = data.get("relativeHumidity", 0.0)
    wind_speed   = ((data.get("wind") or {}).get("speed") or {}).get("value", 0.0)
    rainfall     = ((data.get("precipitation") or {}).get("qpf") or {}).get("quantity", 0.0)

    return {
        "Temperature_C":  float(temperature),
        "Humidity":       float(humidity),
        "Rainfall_mm":    float(rainfall),
        "Wind_Speed_kmh": float(wind_speed),
        "_weather_snapshot": {
            "condition":    ((data.get("weatherCondition") or {}).get("description") or {}).get("text"),
            "feels_like_c": (data.get("feelsLikeTemperature") or {}).get("degrees"),
            "uv_index":     data.get("uvIndex"),
        },
    }


# ── Irrigation route ──────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Smart Irrigation API is running"}


@app.post(
    "/irrigation/predict",
    response_model=IrrigationResponse,
    tags=["Irrigation"],
    summary="Predict irrigation level using live weather + crop data",
)
async def predict_irrigation(request: IrrigationRequest):
    """
    Supply your farm's **coordinates** and **soil/crop details**.
    Weather data (temperature, humidity, rainfall, wind speed) is fetched
    automatically from the Google Weather API — no manual entry needed.
    """
    # 1. Pull live weather for the farm location
    weather = await get_current_weather_data(request.latitude, request.longitude)
    snapshot = weather.pop("_weather_snapshot")

    # 2. Build the full 15-feature input dict
    model_input = {
        "Soil_Moisture":  request.soil_moisture,
        **weather,                                    # 4 weather features auto-filled
        # Season (one-hot — Kharif is the implicit baseline)
        "Rabi":      int(request.season == "Rabi"),
        "Zaid":      int(request.season == "Zaid"),
        # Growth stage (one-hot — Flowering is the implicit baseline)
        "Harvest":   int(request.growth_stage == "Harvest"),
        "Sowing":    int(request.growth_stage == "Sowing"),
        "Vegetative": int(request.growth_stage == "Vegetative"),
        # Crop type (one-hot)
        "Maize":     int(request.crop == "Maize"),
        "Potato":    int(request.crop == "Potato"),
        "Rice":      int(request.crop == "Rice"),
        "Sugarcane": int(request.crop == "Sugarcane"),
        "Wheat":     int(request.crop == "Wheat"),
    }

    # 3. Run the ML model
    irrigation_level = get_irrigation_advice(model_input)

    return IrrigationResponse(
        irrigation_level=irrigation_level,
        weather_used={
            "temperature_c":  weather["Temperature_C"],
            "humidity_pct":   weather["Humidity"],
            "rainfall_mm":    weather["Rainfall_mm"],
            "wind_speed_kmh": weather["Wind_Speed_kmh"],
            **snapshot,
        },
        model_input=model_input,
    )


# ── Raw weather routes (unchanged) ───────────────────────────────────────────

@app.get("/weather/current", response_model=CurrentConditionsResponse, tags=["Weather"])
async def get_current_conditions(lat: float, lng: float, units: str = "METRIC"):
    return await fetch_weather(
        "currentConditions:lookup",
        {"location.latitude": lat, "location.longitude": lng, "unitsSystem": units},
    )


@app.get("/weather/forecast/hourly", response_model=HourlyForecastResponse, tags=["Weather"])
async def get_hourly_forecast(lat: float, lng: float, hours: int = 24, units: str = "METRIC"):
    return await fetch_weather(
        "forecast/hours:lookup",
        {"location.latitude": lat, "location.longitude": lng, "hours": hours, "unitsSystem": units},
    )


@app.get("/weather/forecast/daily", response_model=DailyForecastResponse, tags=["Weather"])
async def get_daily_forecast(lat: float, lng: float, days: int = 5, units: str = "METRIC"):
    return await fetch_weather(
        "forecast/days:lookup",
        {"location.latitude": lat, "location.longitude": lng, "days": days, "unitsSystem": units},
    )


@app.get("/weather/history/hourly", response_model=HistoryResponse, tags=["Weather"])
async def get_hourly_history(lat: float, lng: float, hours: int = 24, units: str = "METRIC"):
    return await fetch_weather(
        "history/hours:lookup",
        {"location.latitude": lat, "location.longitude": lng, "hours": hours, "unitsSystem": units},
    )