import os
from datetime import datetime

class Config:
    """Configuration settings for VyuhMitra application"""

    # API Configuration
    RAILRADAR_API_KEY = "rr_live_tfKPQhebmFotXLyceihcffYvgw3xcMMt"  # From your key
    RAILRADAR_BASE_URL = "https://railradar.in/api/v1"

    # Default section for processing
    DEFAULT_FROM_STATION = "GY"  # Gooty
    DEFAULT_TO_STATION = "GTL"   # Guntakal

    # Optimization parameters (From Indian Railways rule book)
    MIN_HEADWAY_MINUTES = 5  # Minimum time between trains for safety
    MAX_DEVIATION_MINUTES = 120  # Maximum schedule adjustment allowed
    PLATFORM_SEPARATION_MINUTES = 10  # Extra time for same platform trains

    # Abnormality detection thresholds
    DELAY_THRESHOLD_MINUTES = 10  # Delay > 10 min is abnormal
    STOPPAGE_THRESHOLD_MINUTES = 5  # Stopped > 5 min is abnormal

    # Control room response timeout
    CONTROL_ROOM_TIMEOUT_SECONDS = 120  # 2 minutes for control room response

    # Dashboard configuration
    DASHBOARD_HOST = "127.0.0.1"
    DASHBOARD_PORT = 5000
    DASHBOARD_DEBUG = True

    # Data collection settings
    LIVE_DATA_HOURS = 8  # Hours to look ahead for live data
    DATA_REFRESH_INTERVAL = 30  # 30 seconds refresh for real-time detection

    # Solution tracking
    SOLUTION_EXPIRY_MINUTES = 30  # Applied solutions valid for 30 minutes

    # KPI thresholds
    MIN_THROUGHPUT_THRESHOLD = 2.0  # trains per hour
    MAX_THROUGHPUT_THRESHOLD = 8.0  # trains per hour
    EFFICIENCY_TARGET_SCORE = 75.0  # target efficiency score

    # File paths
    DATA_DIR = "data"
    SCHEDULES_DIR = "data/schedules"
    LIVE_DIR = "data/live"
    RESULTS_DIR = "data/results"
    KPI_DIR = "data/kpi"
    ML_MODEL_PATH = "models/reason_model.pkl"
    STATIC_SCHEDULE_FILE = "data.jio"  # JSON for static schedules
    PAST_DATA_FILE = "data/past_abnormalities.json"  # For ML training and what-if

    # Common reasons for delays (from Indian Railways experience)
    COMMON_DELAY_REASONS = [
        "Technical Failure",
        "Track Obstruction",
        "Signal Issue",
        "Weather Disruption",
        "Crew Shortage",
        "Late Running of Connecting Train",
        "Station Congestion",
        "Engineering Work"
    ]

    # Solution types (ways) as per your flow
    SOLUTION_WAYS = [
        "change_track",      # Switch to parallel track
        "change_route",      # Take alternate route
        "replace_train",     # Replace with another train
        "hold_at_station",   # Hold at station temporarily
        "speed_adjustment"   # Adjust speed to recover time
    ]

    # New: Reason to Ways mapping (fix no_ways_found)
    REASON_TO_WAYS = {
        "Crew Shortage": ["replace_train", "hold_at_station"],
        "Technical Failure": ["replace_train", "change_track"],
        "Track Obstruction": ["change_route", "hold_at_station"],
        "Signal Issue": ["change_track", "speed_adjustment"],
        "Weather Disruption": ["change_route", "hold_at_station"],
        "Late Running of Connecting Train": ["speed_adjustment", "change_route"],
        "Station Congestion": ["change_track", "hold_at_station"],
        "Engineering Work": ["change_route", "change_track"]
    }

    # ML Confidence threshold
    MIN_CONFIDENCE = 0.5

    # Rejection reasons for ML learning
    REJECTION_REASONS = [
        "Not Feasible",
        "Safety Concern",
        "Cost Too High",
        "Better Alternative",
        "Other"
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