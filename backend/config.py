import os
from datetime import datetime


class Config:
    # RailRadar API Configuration
    RAILRADAR_API_KEY = "QUxMIFlPVVIgQkFTRSBBUkUgQkVMT05HIFRPIFVT"  # From documentation example
    RAILRADAR_BASE_URL = "https://railradar.in/api/v1"

    # Section Configuration - GY to GTL
    DEFAULT_FROM_STATION = "GY"  # Gooty
    DEFAULT_TO_STATION = "GTL"  # Guntakal

    # Abnormality Detection Thresholds
    DELAY_THRESHOLD_MINUTES = 10
    STOPPAGE_THRESHOLD_MINUTES = 5

    # Control Room Configuration
    CONTROL_ROOM_TIMEOUT_SECONDS = 120  # 2 minutes

    # ML Model Configuration
    ML_MODEL_PATH = "models/reason_model.pkl"

    # Solution Configuration
    SOLUTION_EXPIRY_MINUTES = 60
    MIN_HEADWAY_MINUTES = 5
    MAX_DEVIATION_MINUTES = 120

    # Data Files
    STATIC_SCHEDULE_FILE = "data.jio"
    DATA_DIR = "data"
    SCHEDULES_DIR = "data/schedules"
    LIVE_DIR = "data/live"
    RESULTS_DIR = "data/results"
    KPI_DIR = "data/kpi"

    # Dashboard Configuration
    DASHBOARD_HOST = "127.0.0.1"
    DASHBOARD_PORT = 5000
    DASHBOARD_DEBUG = True

    # Common delay reasons for ML training
    COMMON_DELAY_REASONS = [
        "Technical Failure",
        "Track Obstruction",
        "Signal Issue",
        "Weather Disruption",
        "Crew Shortage",
        "Engineering Work",
        "Station Congestion",
        "Late Running of Connecting Train"
    ]

    # Section Boundaries (stations to monitor before/after section)
    SECTION_BOUNDARY_STATIONS = {
        "GY": ["DHNE", "GY", "TNGL"],  # Stations around Gooty
        "GTL": ["TNGL", "GTL", "ATP"]  # Stations around Guntakal
    }

    # Optimization Configuration
    EFFICIENCY_TARGET_SCORE = 85

    @staticmethod
    def get_timestamp():
        return datetime.now().isoformat()

    @staticmethod
    def get_date():
        return datetime.now().strftime("%Y-%m-%d")
