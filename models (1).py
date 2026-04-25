from pydantic import BaseModel, Field
from typing import Optional, List, Literal


# ── Irrigation request/response ───────────────────────────────────────────────

class IrrigationRequest(BaseModel):
    # Farm location — used to auto-fetch weather
    latitude:  float = Field(..., example=19.0760, description="Farm latitude")
    longitude: float = Field(..., example=72.8777, description="Farm longitude")

    # Sensor reading
    soil_moisture: float = Field(..., example=25.5, description="Soil moisture (%)")

    # Categorical inputs (string-based, cleaner than sending raw one-hot vectors)
    season: Literal["Kharif", "Rabi", "Zaid"] = Field(
        ..., example="Zaid", description="Current agricultural season"
    )
    growth_stage: Literal["Sowing", "Vegetative", "Flowering", "Harvest"] = Field(
        ..., example="Vegetative", description="Current crop growth stage"
    )
    crop: Literal["Maize", "Potato", "Rice", "Sugarcane", "Wheat"] = Field(
        ..., example="Rice", description="Crop type"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 19.0760,
                "longitude": 72.8777,
                "soil_moisture": 25.5,
                "season": "Zaid",
                "growth_stage": "Vegetative",
                "crop": "Rice",
            }
        }


class IrrigationResponse(BaseModel):
    irrigation_level: str = Field(..., description="Predicted level: Low / Medium / High")
    weather_used: dict  = Field(..., description="Live weather data fetched from Google API")
    model_input: dict   = Field(..., description="Full 15-feature vector passed to the model")


# ── Shared Weather primitives ─────────────────────────────────────────────────

class ValueWithUnit(BaseModel):
    degrees:  Optional[float] = None
    value:    Optional[float] = None
    unit:     Optional[str]   = None
    quantity: Optional[float] = None


class WeatherCondition(BaseModel):
    iconBaseUri: Optional[str]  = None
    description: Optional[dict] = None
    type:        Optional[str]  = None


class Wind(BaseModel):
    direction: Optional[dict]         = None
    speed:     Optional[ValueWithUnit] = None
    gust:      Optional[ValueWithUnit] = None


class Precipitation(BaseModel):
    probability: Optional[dict]         = None
    qpf:         Optional[ValueWithUnit] = None


class TimeZone(BaseModel):
    id: Optional[str] = None


# ── Current Conditions ────────────────────────────────────────────────────────

class CurrentConditionsResponse(BaseModel):
    currentTime:         Optional[str]          = None
    timeZone:            Optional[TimeZone]      = None
    isDaytime:           Optional[bool]          = None
    weatherCondition:    Optional[WeatherCondition] = None
    temperature:         Optional[ValueWithUnit] = None
    feelsLikeTemperature: Optional[ValueWithUnit] = None
    dewPoint:            Optional[ValueWithUnit] = None
    heatIndex:           Optional[ValueWithUnit] = None
    windChill:           Optional[ValueWithUnit] = None
    relativeHumidity:    Optional[int]           = None
    uvIndex:             Optional[int]           = None
    precipitation:       Optional[Precipitation] = None
    wind:                Optional[Wind]          = None
    visibility:          Optional[ValueWithUnit] = None
    cloudCover:          Optional[int]           = None
    pressure:            Optional[ValueWithUnit] = None


# ── Hourly Forecast ───────────────────────────────────────────────────────────

class HourlyForecastItem(BaseModel):
    interval:              Optional[dict]           = None
    weatherCondition:      Optional[WeatherCondition] = None
    temperature:           Optional[ValueWithUnit]  = None
    feelsLikeTemperature:  Optional[ValueWithUnit]  = None
    dewPoint:              Optional[ValueWithUnit]  = None
    relativeHumidity:      Optional[int]            = None
    uvIndex:               Optional[int]            = None
    precipitation:         Optional[Precipitation]  = None
    thunderstormProbability: Optional[int]          = None
    wind:                  Optional[Wind]           = None
    cloudCover:            Optional[int]            = None
    visibility:            Optional[ValueWithUnit]  = None
    isDaytime:             Optional[bool]           = None


class HourlyForecastResponse(BaseModel):
    forecastHours: Optional[List[HourlyForecastItem]] = None
    timeZone:      Optional[TimeZone]                 = None


# ── Daily Forecast ────────────────────────────────────────────────────────────

class DayPeriodForecast(BaseModel):
    interval:               Optional[dict]          = None
    weatherCondition:       Optional[WeatherCondition] = None
    relativeHumidity:       Optional[int]           = None
    uvIndex:                Optional[int]           = None
    precipitation:          Optional[Precipitation] = None
    thunderstormProbability: Optional[int]          = None
    wind:                   Optional[Wind]          = None
    cloudCover:             Optional[int]           = None


class DailyForecastItem(BaseModel):
    interval:              Optional[dict]            = None
    displayDate:           Optional[dict]            = None
    daytimeForecast:       Optional[DayPeriodForecast] = None
    nighttimeForecast:     Optional[DayPeriodForecast] = None
    maxTemperature:        Optional[ValueWithUnit]   = None
    minTemperature:        Optional[ValueWithUnit]   = None
    feelsLikeMaxTemperature: Optional[ValueWithUnit] = None
    feelsLikeMinTemperature: Optional[ValueWithUnit] = None
    sunEvents:             Optional[dict]            = None
    moonEvents:            Optional[dict]            = None


class DailyForecastResponse(BaseModel):
    forecastDays: Optional[List[DailyForecastItem]] = None
    timeZone:     Optional[TimeZone]                = None


# ── Historical ────────────────────────────────────────────────────────────────

class HistoryResponse(BaseModel):
    historyHours: Optional[List[HourlyForecastItem]] = None
    timeZone:     Optional[TimeZone]                 = None