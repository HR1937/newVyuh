import os
from datetime import datetime

class Config:
    """Configuration settings for VyuhMitra application"""

    # API Configuration (prefer environment variables, fallback to provided constants)
    RAILRADAR_API_KEY = os.environ.get("RAILRADAR_API_KEY") or "rr_live_tfKPQhebmFotXLyceihcffYvgw3xcMMt"
    RAILRADAR_BASE_URL = os.environ.get("RAILRADAR_BASE_URL") or "https://railradar.in/api/v1"

    # Default section for processing
    DEFAULT_FROM_STATION = os.environ.get("DEFAULT_FROM_STATION", "GY")   # Gooty
    DEFAULT_TO_STATION = os.environ.get("DEFAULT_TO_STATION", "GTL")      # Guntakal

    # Optimization parameters (From Indian Railways rule book)
    MIN_HEADWAY_MINUTES = int(os.environ.get("MIN_HEADWAY_MINUTES", "5"))    # Minimum time between trains for safety
    MAX_DEVIATION_MINUTES = int(os.environ.get("MAX_DEVIATION_MINUTES", "120"))
    PLATFORM_SEPARATION_MINUTES = int(os.environ.get("PLATFORM_SEPARATION_MINUTES", "10"))

    # Abnormality detection thresholds
    DELAY_THRESHOLD_MINUTES = int(os.environ.get("DELAY_THRESHOLD_MINUTES", "10"))   # Delay > 10 min is abnormal
    STOPPAGE_THRESHOLD_MINUTES = int(os.environ.get("STOPPAGE_THRESHOLD_MINUTES", "5"))

    # Control room response timeout
    CONTROL_ROOM_TIMEOUT_SECONDS = int(os.environ.get("CONTROL_ROOM_TIMEOUT_SECONDS", "120"))  # 2 minutes

    # Dashboard configuration
    DASHBOARD_HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
    DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", "5000"))
    DASHBOARD_DEBUG = os.environ.get("DASHBOARD_DEBUG", "true").lower() == "true"

    # Data collection settings
    LIVE_DATA_HOURS = int(os.environ.get("LIVE_DATA_HOURS", "8"))   # Hours to look ahead for live data
    DATA_REFRESH_INTERVAL = int(os.environ.get("DATA_REFRESH_INTERVAL", "30"))  # seconds

    # Solution tracking
    SOLUTION_EXPIRY_MINUTES = int(os.environ.get("SOLUTION_EXPIRY_MINUTES", "30"))  # Applied solutions valid for 30 minutes
    SOLUTION_COOLDOWN_MINUTES = int(os.environ.get("SOLUTION_COOLDOWN_MINUTES", "10"))  # prevent immediate re-detection

    # KPI thresholds
    MIN_THROUGHPUT_THRESHOLD = float(os.environ.get("MIN_THROUGHPUT_THRESHOLD", "2.0"))
    MAX_THROUGHPUT_THRESHOLD = float(os.environ.get("MAX_THROUGHPUT_THRESHOLD", "8.0"))
    EFFICIENCY_TARGET_SCORE = float(os.environ.get("EFFICIENCY_TARGET_SCORE", "75.0"))

    # File paths
    DATA_DIR = os.environ.get("DATA_DIR", "data")
    SCHEDULES_DIR = os.environ.get("SCHEDULES_DIR", "data/schedules")
    LIVE_DIR = os.environ.get("LIVE_DIR", "data/live")
    RESULTS_DIR = os.environ.get("RESULTS_DIR", "data/results")
    KPI_DIR = os.environ.get("KPI_DIR", "data/kpi")
    ML_MODEL_PATH = os.environ.get("ML_MODEL_PATH", "models/reason_model.pkl")
    STATIC_SCHEDULE_FILE = os.environ.get("STATIC_SCHEDULE_FILE", "data.jio")  # your static schedule

    # Common reasons for delays (from Indian Railways experience)
    COMMON_DELAY_REASONS = [
        "Technical Failure",
        "Track Obstruction",
        "Signal Issue",
        "Weather Disruption",
        "Crew Shortage",
        "Late Running of Connecting Train",
        "Station Congestion",
        "Engineering Work",
    ]

    # Solution types (ways) as per your flow
    SOLUTION_WAYS = [
        "change_track",       # Switch to parallel track
        "change_route",       # Take alternate route
        "replace_train",      # Replace with another train
        "hold_at_station",    # Hold at station temporarily
        "speed_adjustment",   # Adjust speed to recover time
    ]

    @staticmethod
    def get_timestamp():
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def get_date():
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def get_time():
        return datetime.now().strftime("%H:%M:%S")
