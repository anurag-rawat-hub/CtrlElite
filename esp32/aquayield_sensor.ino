/*
 * ============================================================
 *  AquaYield ESP32 — Sensor Node
 * ============================================================
 *  Sensors:
 *    - DHT11 / DHT22  → Temperature & Humidity  (GPIO 4)
 *    - Soil Moisture   → Analog capacitive sensor (GPIO 34)
 *    - MQ-135          → Air/Gas quality (ppm)   (GPIO 35)
 *
 *  Sends a POST to Django backend every 10 seconds:
 *    POST http://<YOUR_PC_IP>:8000/api/sensor/
 *    Body: { soil, temp, hum, gas, device_id }
 * ============================================================
 *  Libraries needed (install via Arduino Library Manager):
 *    - DHT sensor library by Adafruit
 *    - Adafruit Unified Sensor
 *    - ArduinoJson  (by Benoit Blanchon, v6.x)
 * ============================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ── WiFi Credentials ────────────────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";       // << CHANGE THIS
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";   // << CHANGE THIS

// ── Backend URL ─────────────────────────────────────────────
// Use your PC's local IP address (run `ipconfig` on Windows)
// NOT localhost — the ESP32 is a separate device on your network.
const char* SERVER_URL = "http://192.168.1.X:8000/api/sensor/";  // << CHANGE THIS

// ── Device ID ────────────────────────────────────────────────
const char* DEVICE_ID = "esp32_node_01";

// ── PIN Definitions ──────────────────────────────────────────
#define DHT_PIN         4       // DHT11/DHT22 data pin
#define DHT_TYPE        DHT11   // Change to DHT22 if you use DHT22
#define SOIL_PIN        34      // Analog soil moisture sensor
#define GAS_PIN         35      // MQ-135 analog output
#define RELAY_PIN       26      // Water Pump Relay Module

// ── Sensor Calibration ───────────────────────────────────────
// Soil moisture: raw ADC values (0–4095 on ESP32)
const int SOIL_DRY = 3200;
const int SOIL_WET = 1200;

// ── Interval & Timers ────────────────────────────────────────
const unsigned long SEND_INTERVAL_MS = 3000;
unsigned long lastSendTime = 0;

bool pumpActive = false;
unsigned long pumpStartTime = 0;
unsigned long pumpDurationMs = 0;

// ── Object Init ──────────────────────────────────────────────
DHT dht(DHT_PIN, DHT_TYPE);

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== AquaYield Sensor Node Booting ===");

  // Init Relay
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW); // Start with pump OFF

  // Init DHT
  dht.begin();

  // ── Force 2.4GHz station mode (important!) ──
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);   // Don't cache credentials — prevents stale config issues
  delay(1500);

  // Connect to WiFi
  Serial.printf("\nConnecting to WiFi: '%s'\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    retries++;

    if (retries % 10 == 0) {
      Serial.printf("\n  Still trying... (attempt %d)", retries);
      Serial.printf("\n  WiFi Status code: %d", WiFi.status());
      // Status codes:
      // 0 = WL_IDLE_STATUS
      // 1 = WL_NO_SSID_AVAIL  ← wrong SSID / out of range
      // 4 = WL_CONNECT_FAILED ← wrong password
      // 6 = WL_DISCONNECTED
    }

    if (retries > 60) {
      Serial.println("\n\n✗ WiFi connection FAILED after 30s.");
      Serial.println("  Possible causes:");
      Serial.println("  1. Wrong SSID or password (case-sensitive!)");
      Serial.println("  2. Router is 5GHz only (ESP32 only supports 2.4GHz)");
      Serial.println("  3. Router uses WPA3 — switch to WPA2 in router settings");
      Serial.println("  Restarting in 5 seconds...");
      delay(5000);
      ESP.restart();
    }
  }

  Serial.println("\n✓ WiFi connected!");
  Serial.printf("  IP Address  : %s\n", WiFi.localIP().toString().c_str());
  Serial.printf("  Signal (dBm): %d\n", WiFi.RSSI());
  Serial.printf("  Channel     : %d\n", WiFi.channel());
}

// ─────────────────────────────────────────────────────────────
void loop() {
  unsigned long currentMillis = millis();

  // ── 1. Non-blocking Relay Timer ──
  if (pumpActive && (currentMillis - pumpStartTime >= pumpDurationMs)) {
    pumpActive = false;
    digitalWrite(RELAY_PIN, LOW);
    Serial.println("\n[PUMP] ⏱️ Timer finished. Relay turned OFF.");
  }

  // ── 1.5. Emergency Flood Shutoff (Immediate) ──
  if (pumpActive) {
    int liveSoil = analogRead(SOIL_PIN);
    float livePercent = constrain(map(liveSoil, SOIL_DRY, SOIL_WET, 0, 100), 0.0f, 100.0f);
    if (livePercent >= 100.0f) {
      pumpActive = false;
      digitalWrite(RELAY_PIN, LOW);
      Serial.println("\n[EMERGENCY] 🛑 Soil Moisture hit 100%! Pump instantly terminated.");
    }
  }

  // ── 2. Data Upload Interval ──
  if (currentMillis - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = currentMillis;

    // ── Read DHT ──
    float temperature = dht.readTemperature();
    float humidity    = dht.readHumidity();

    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("[WARN] DHT read failed — skipping cycle.");
      return;
    }

    // ── Read Soil Moisture (convert ADC → percentage) ──
    int soilRaw = analogRead(SOIL_PIN);
    float soilPercent = map(soilRaw, SOIL_DRY, SOIL_WET, 0, 100);
    soilPercent = constrain(soilPercent, 0.0f, 100.0f);

    // ── Read Gas (MQ-135 raw ADC → approximate ppm) ──
    int gasRaw = analogRead(GAS_PIN);
    float gasPpm = (gasRaw / 4095.0f) * 1000.0f;

    // ── Print readings to Serial ──
    Serial.println("─────────────────────────────");
    Serial.printf("  Temp      : %.1f °C\n",  temperature);
    Serial.printf("  Humidity  : %.1f %%\n",  humidity);
    Serial.printf("  Soil (raw): %d → %.1f %%\n", soilRaw, soilPercent);
    Serial.printf("  Gas  (raw): %d → %.1f ppm\n", gasRaw, gasPpm);

    // ── Build JSON payload ──
    StaticJsonDocument<200> doc;
    doc["soil"]      = soilPercent;
    doc["temp"]      = temperature;
    doc["hum"]       = humidity;
    doc["gas"]       = gasPpm;
    doc["device_id"] = DEVICE_ID;

    String jsonBody;
    serializeJson(doc, jsonBody);

    // ── Send POST to Django backend ──
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(SERVER_URL);
      http.addHeader("Content-Type", "application/json");

      Serial.println("  Sending POST to backend...");
      int httpCode = http.POST(jsonBody);

      if (httpCode > 0) {
        String response = http.getString();
        Serial.printf("  ✓ HTTP %d\n", httpCode);
        Serial.printf("  Response: %s\n", response.c_str());

        // Parse JSON for pump timer instructions
        StaticJsonDocument<256> respDoc;
        DeserializationError err = deserializeJson(respDoc, response);
        if (!err && respDoc.containsKey("pump_time_min")) {
          float mins = respDoc["pump_time_min"];
          if (mins > 0) {
            pumpActive = true;
            pumpStartTime = currentMillis;
            pumpDurationMs = (unsigned long)(mins * 1000UL); // DEMO MODE: Treats minutes as seconds
            digitalWrite(RELAY_PIN, HIGH);
            Serial.printf("  [PUMP] 💦 Turned ON for %.1f demo-seconds.\n", mins);
          }
        }
      } else {
        Serial.printf("  ✗ POST failed: %s\n", http.errorToString(httpCode).c_str());
      }

      http.end();
    } else {
      Serial.println("  [WARN] WiFi disconnected — reconnecting...");
      WiFi.reconnect();
    }
  }
}
