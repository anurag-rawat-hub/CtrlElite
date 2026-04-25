from django.db import models


class SensorReading(models.Model):
    device_id = models.CharField(max_length=100, default="device_01")
    soil_moisture = models.FloatField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    gas = models.FloatField(default=0)
    water_flow_req = models.CharField(max_length=50, null=True, blank=True)
    pump_time_min = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.device_id} @ {self.timestamp}"
