from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import HttpResponse
import joblib
import os
import requests
import pandas as pd
from django.utils import timezone
from datetime import timedelta
from .models import SensorReading

# Load model using BASE_DIR-relative path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "api", "irrigation_prediction_v2.joblib")
with open(MODEL_PATH, "rb") as f:
    model = joblib.load(f)

OLLAMA_URL = "http://localhost:11434/api/generate"

def send_whatsapp_alert(message: str):
    """Sends a WhatsApp alert via Twilio API, pulling credentials from environment variables."""
    TWILIO_SID = os.environ.get("TWILIO_SID")
    TWILIO_AUTH = os.environ.get("TWILIO_AUTH")
    TWILIO_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
    TWILIO_TO = os.environ.get("TWILIO_WHATSAPP_TO")

    if not all([TWILIO_SID, TWILIO_AUTH, TWILIO_FROM, TWILIO_TO]):
        print("Twilio warning: Missing .env credentials. WhatsApp skipped.")
        return

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
    auth = (TWILIO_SID, TWILIO_AUTH)
    data = {"From": TWILIO_FROM, "To": TWILIO_TO, "Body": message}
    try:
        res = requests.post(url, auth=auth, data=data, timeout=5)
        if res.status_code in [200, 201]:
            print("✓ WhatsApp Alert successfully sent.")
        else:
            print("✗ Twilio rejected the message:", res.text)
    except Exception as e:
        print("✗ Twilio network error:", str(e))

LAST_ALERT_TIME = {
    "drought": None,
    "flood": None
}

def check_and_send_alert(alert_type: str, message: str):
    """Sends alert if not sent recently (10 mins cooldown)"""
    now = timezone.now()
    last_time = LAST_ALERT_TIME.get(alert_type)
    
    # Send if never sent, OR if 10 full minutes have elapsed
    if last_time is None or (now - last_time) > timedelta(minutes=10):
        send_whatsapp_alert(message)
        LAST_ALERT_TIME[alert_type] = now


def home(request):
    return HttpResponse("AquaYield Backend Running 🚀")


def get_current_weather_sync(lat: float, lng: float) -> dict:
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    default_weather = {
        "Rainfall_mm": 0.0,
        "Wind_Speed_kmh": 12.5,
    }
    
    if not GOOGLE_API_KEY:
        return default_weather
        
    try:
        url = "https://weather.googleapis.com/v1/currentConditions:lookup"
        params = {
            "key": GOOGLE_API_KEY,
            "location.latitude": lat,
            "location.longitude": lng,
            "unitsSystem": "METRIC",
        }
        resp = requests.get(url, params=params, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            wind_speed = ((data.get("wind") or {}).get("speed") or {}).get("value", default_weather["Wind_Speed_kmh"])
            rainfall = ((data.get("precipitation") or {}).get("qpf") or {}).get("quantity", default_weather["Rainfall_mm"])
            return {
                "Rainfall_mm": float(rainfall),
                "Wind_Speed_kmh": float(wind_speed),
            }
    except Exception as e:
        print("Weather API Error:", e)
        
    return default_weather

@api_view(["GET"])
def latest_reading(request):
    """Return the most recent sensor reading."""
    reading = SensorReading.objects.first()
    if not reading:
        return Response({"error": "No data yet"}, status=404)
    return Response({
        "device_id": reading.device_id,
        "soil_moisture": reading.soil_moisture,
        "temperature": reading.temperature,
        "humidity": reading.humidity,
        "gas": reading.gas,
        "water_flow_req": reading.water_flow_req,
        "pump_time_min": reading.pump_time_min,
        "timestamp": reading.timestamp.isoformat(),
    })


@api_view(["GET"])
def sensor_history(request):
    """Return last 20 sensor readings for history table."""
    readings = SensorReading.objects.all()[:20]
    data = []
    for r in readings:
        data.append({
            "device_id": r.device_id,
            "soil_moisture": r.soil_moisture,
            "temperature": r.temperature,
            "humidity": r.humidity,
            "gas": r.gas,
            "water_flow_req": r.water_flow_req,
            "pump_time_min": r.pump_time_min,
            "timestamp": r.timestamp.isoformat(),
        })
    return Response(data)


@api_view(["POST"])
def sensor_data(request):
    """Accept sensor data, run ML prediction, save to DB, return result."""
    try:
        soil = float(request.data.get("soil", 0))
        temp = float(request.data.get("temp", 0))
        hum = float(request.data.get("hum", 0))
        gas = float(request.data.get("gas", 0))
        device_id = request.data.get("device_id", "device_01")
    except (TypeError, ValueError) as e:
        return Response({"error": f"Invalid data: {e}"}, status=400)

    # Find previous reading for Edge-Trigger evaluations
    last_reading = SensorReading.objects.first()
    last_pump = getattr(last_reading, 'pump_time_min', 0.0) if last_reading else 0.0

    if soil >= 100.0:
        predicted_label = "Emergency Flood Control"
        pump_time_min = 0.0
        # Trigger Twilio only exactly when it shifts
        if getattr(last_reading, 'soil_moisture', 50.0) < 100.0 or last_pump > 0.0:
            send_whatsapp_alert("🛑 *AquaYield Alert*: Soil moisture hit 100%! You need to stop the pump. Emergency shutdown engaged.")
        else:
            # If still flooded after 10 mins without being fixed
            check_and_send_alert("flood", "🛑 *REMINDER*: Soil moisture is STILL at 100%! Please fix the flooding issue.")
            
    elif soil <= 0.0:
        predicted_label = "High"
        pump_time_min = 15.0
        if getattr(last_reading, 'soil_moisture', 50.0) > 0.0 or last_pump == 0.0:
            send_whatsapp_alert("*AquaYield Alert*: Soil moisture hit 0%! Pump has been forcefully started to save crops.")
        else:
            # If still at 0% after 10 mins without being fixed
            check_and_send_alert("drought", " *REMINDER*: Soil moisture is STILL at 0% after 10 minutes! Pump is active but not repairing the drought.")
            
    elif soil > 70.0:
        predicted_label = "Optimal Moisture"
        pump_time_min = 0.0
    else:
        # Fetch live weather (Rain and Wind) for a generic farm location (e.g. Mumbai)
        weather = get_current_weather_sync(19.0760, 72.8777)
        
        # ML Prediction using the new 15-feature model (v2)
        input_data = {
            "Soil_Moisture": soil,
            "Temperature_C": temp,      # Use ESP32 live temperature
            "Humidity": hum,            # Use ESP32 live humidity
            "Rainfall_mm": weather["Rainfall_mm"],
            "Wind_Speed_kmh": weather["Wind_Speed_kmh"],
            "Rabi": 0,
            "Zaid": 1,
            "Harvest": 0,
            "Sowing": 0,
            "Vegetative": 1,
            "Maize": 0,
            "Potato": 0,
            "Rice": 1,
            "Sugarcane": 0,
            "Wheat": 0,
        }
        
        df_input = pd.DataFrame([input_data])
        prediction = model.predict(df_input)[0]

        if not isinstance(prediction, str):
            mapping = {0: "Low", 1: "Medium", 2: "High"}
            predicted_label = mapping.get(prediction, "Unknown")
        else:
            predicted_label = prediction

        # Proportional mapping: High = 15 mins, Medium = 10 mins, Low = 5 mins
        if predicted_label == "High":
            pump_time_min = 15.0
        elif predicted_label == "Medium":
            pump_time_min = 10.0
        elif predicted_label == "Low":
            pump_time_min = 5.0
        else:
            pump_time_min = 0.0

        # Normal ML Twilio Logic
        if pump_time_min > 0.0 and last_pump == 0.0:
            whatsapp_msg = (
                f"💦 *AquaYield Alert*: Pump Activated via AI Logic!\n"
                f"Prediction: {predicted_label}\n"
                f"Duration Scheduled: {pump_time_min} seconds."
            )
            send_whatsapp_alert(whatsapp_msg)

    # Save reading to database
    SensorReading.objects.create(
        device_id=device_id,
        soil_moisture=soil,
        temperature=temp,
        humidity=hum,
        gas=gas,
        water_flow_req=predicted_label,
        pump_time_min=pump_time_min,
    )

    return Response({
        "water_flow_req": predicted_label,
        "pump_time_min": pump_time_min,
        "device_id": device_id,
    })


@api_view(["GET"])
def get_ai_advice(request):
    """Fetch the latest reading and ask Llama3.1 for advice."""
    reading = SensorReading.objects.first()
    if not reading:
        return Response({"error": "No sensor data available for advice."}, status=404)

    prompt = (
        "You are an expert AI agronomist. Below is the real-time sensor data from a farm:\n"
        f"- Soil Moisture: {reading.soil_moisture}%\n"
        f"- Temperature: {reading.temperature}°C\n"
        f"- Humidity: {reading.humidity}%\n"
        f"- Air Quality (Gas levels): {reading.gas} ppm\n\n"
        "Based on this data, provide specific, actionable irrigation advice and crop care for crop health, "
        "irrigation requirements, and any potential risks regarding air quality or temperature. "
        "Keep it concise (3-4 sentences maximum). Print the temperature, humidity, and gas levels of that moment in the start of the response "
    )

    try:
        ollama_res = requests.post(
            OLLAMA_URL,
            json={"model": "llama3.1", "prompt": prompt, "stream": False},
            timeout=120,
        )
        ai_output = ollama_res.json().get("response", "Could not generate advice.")
    except Exception as e:
        ai_output = f"AI assistant offline or error: {str(e)}"

    return Response({
        "advice": ai_output,
        "timestamp": reading.timestamp.isoformat()
    })


@api_view(["POST"])
def chat_ai(request):
    """Handle generic chat messages using Llama3.1."""
    user_message = request.data.get("message")
    if not user_message:
        return Response({"error": "Message is required."}, status=400)

    # Optional: Include latest sensor data as context automatically, 
    # so the bot always knows the current farm state.
    context = ""
    reading = SensorReading.objects.first()
    if reading:
        context = (
            f"[System Context - Current Farm Sensor Data: Moisture {reading.soil_moisture}%, "
            f"Temp {reading.temperature}°C, Humidity {reading.humidity}%, Gas {reading.gas} ppm]\n\n"
        )

    prompt = (
        "You are an expert AI agronomist assistant. You help farmers manage crops, "
        "irrigation, and disease control based on their questions and current sensor data. "
        "Keep your answers concise and highly relevant.\n\n"
        f"{context}"
        f"Farmer User: {user_message}\n"
        "AI Agronomist: "
    )

    try:
        ollama_res = requests.post(
            OLLAMA_URL,
            json={"model": "llama3.1", "prompt": prompt, "stream": False},
            timeout=120,
        )
        ai_output = ollama_res.json().get("response", "I'm having trouble thinking right now.")
    except Exception as e:
        ai_output = f"AI assistant offline or error: {str(e)}"

    return Response({"response": ai_output})


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(["POST"])
def twilio_webhook(request):
    """
    Standard Webhook Endpoint for Twilio (/api/whatsapp/).
    Allows Twilio to verify connectivity and handles incoming replies from Whatsapp.
    """
    # Create simple TwiML format XML string for twilio auto-replies
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>AquaYield automated system received your message. Live Monitoring is fully active.</Message>
</Response>"""

    return HttpResponse(twiml_response, content_type="text/xml")