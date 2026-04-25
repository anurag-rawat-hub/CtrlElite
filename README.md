

# 💧 AquaYeild: Smart Irrigation System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Hardware: ESP32/Arduino](https://img.shields.io/badge/Hardware-ESP32%2FArduino-orange.svg)](https://www.espressif.com/)

**AquaYeild** is a precision agriculture solution that merges **Israel’s high-efficiency irrigation frameworks** with **Machine Learning** to solve the global water crisis in farming. 

Traditional irrigation methods waste up to 60% of water. AquaYeild reduces this waste by using predictive intelligence to deliver exactly what the crop needs—nothing more, nothing less.

---

## 📍 Table of Contents
- [The Core Pillars](#-the-core-pillars)
- [Key Features](#-key-features)
- [Performance Data](#-performance-data)
- [System Architecture](#-system-architecture)
- [Screenshots](#-screenshots)
- [Installation](#-installation)
- [Future Roadmap](#-future-roadmap)

---

## 🏛️ The Core Pillars

### 1. The Israel Framework (Hardware)
Inspired by the world leader in water conservation, we utilize:
* **Precision Drip Network:** Targeted water delivery via branched pipes.

### 2. Predictive ML Intelligence (Software)
Moving beyond simple timers, our "Decision Engine" uses:
* **Multi-Sensor Fusion:** Real-time data from soil moisture, humidity, and gas sensors.
* **Weather API Correlation:** Our ML model cross-references local soil conditions with 24-hour weather forecasts.
* **Smart Suppression:** If rain is predicted, the system automatically cancels irrigation cycles, saving significant water.

---

## ✨ Key Features
* ✅ **Real-time Monitoring:** View field status via a web dashboard.
* ✅ **WhatsApp Integration:** Get alerts via a simple chat interface.
* ✅ **Water-Saving Logic:** Predictive algorithms that account for evaporation rates and wind speed.

---

## 📊 Performance Data
| Metric | Flood Irrigation | Ceres-Flow (Our System) |
| :--- | :--- | :--- |
| **Water Waste** | High (Runoff/Evaporation) | **Minimal (Precision Drip)** |
| **Operation** | Manual / Reactive | **Autonomous / Predictive** |
| **Resource Savings** | 0% | **~60% Reduction** |

---

## 🏗️ System Architecture
1.  **Perception Layer:** Soil sensors and DHT11 collect environmental data.
2.  **Processing Layer:** ESP32/Arduino transmits data to a Python-based ML backend.
3.  **Action Layer:** Microcontroller triggers Solenoid valves based on ML predictions.
4.  **User Layer:** Dashboard and WhatsApp bot provide human-in-the-loop control.

---

## 📸 Screenshots

| **Web Dashboard** | **WhatsApp Bot** |
| :---: | :---: |
<img width="1873" height="899" alt="Screenshot 2026-04-25 110533" src="https://github.com/user-attachments/assets/f8c2ab50-ad40-4a41-bd56-418a40fef38a" />
<img width="1915" height="883" alt="Screenshot 2026-04-25 110617" src="https://github.com/user-attachments/assets/9a6405e7-413d-44b3-9e16-524fd1ee5b26" />
| ![WhatsApp]  |
| *Real-time analytics & graphs* | *Remote commands & alerts* |

---

## 🛠️ Installation

### Prerequisites
* Python 3.10+
* Arduino IDE (for microcontroller firmware)
* API Key from OpenWeatherMap

### Setup
1.  **Clone the repo:**
    ```bash
    git clone https://github.com/your-username/Ceres-Flow.git
    cd Ceres-Flow
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure environment:**
    Create a `.env` file:
    ```env
    WEATHER_API_KEY=your_api_key
    WHATSAPP_TOKEN=your_token
    ```
4.  **Run the application:**
    ```bash
    python main.py
    ```

---

## 🚀 Future Roadmap
- [ ] Integration of AI-driven pest detection.
- [ ] Solar-powered sensor nodes for total off-grid operation.
- [ ] Expansion to multi-acre mesh network support.

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
