from django.urls import path
from .views import sensor_data, latest_reading, sensor_history, get_ai_advice, chat_ai, twilio_webhook

urlpatterns = [
    path("sensor/", sensor_data),
    path("latest/", latest_reading),
    path("history/", sensor_history),
    path("advice/", get_ai_advice),
    path("chat/", chat_ai),
    path("whatsapp/", twilio_webhook),
]