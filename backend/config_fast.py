import os
from datetime import datetime

class Config:
    """Fast configuration for VyuhMitra system with REAL live data and reduced rate limits"""
    
    # RailRadar API Configuration - REAL WORKING KEY
    RAILRADAR_API_KEY = "rr_live_ccW7ci-7ty2l8DR_yceDZjpJf9PaIPKg"  # REAL working key from text.py
    RAILRADAR_BASE_URL = "https://railradar.in/api/v1"
    
    # Gemini API Configuration  
    GEMINI_API_KEY = "AIzaSyACfh5_Vvhmg_S2aoCH95KYIfprGG4PQiE"
    
    # Section Configuration - REAL ROUTE WITH LIVE TRAINS
    DEFAULT_FROM_STATION = "NDLS"  # New Delhi (34 active trains found!)
    DEFAULT_TO_STATION = "AGC"     # Agra Cantt (popular route with live data)
    
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
    MAX_DELAY_THRESHOLD = 30
    SAFETY_BUFFER_MINUTES = 2
    
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
    
    # Rate limiting - MUCH FASTER for responsive UI
    RAILRADAR_MIN_REQUEST_INTERVAL = 30  # Reduced from 120 to 30 seconds for faster responses
    
    # Demo data control - DISABLED by default for REAL data
    ENABLE_DEMO = os.environ.get('ENABLE_DEMO', '0') == '1'
    
    # Force heuristic solver (avoid CP-SAT crashes)
    FORCE_HEURISTIC_SOLVER = True
    
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
        "NDLS": ["DLI", "NDLS", "GZB"],  # Stations around New Delhi
        "AGC": ["MTJ", "AGC", "BCP"]     # Stations around Agra Cantt
    }
    
    # Optimization Configuration
    EFFICIENCY_TARGET_SCORE = 85
    
    @staticmethod
    def get_timestamp():
        return datetime.now().isoformat()
    
    @staticmethod
    def get_date():
        return datetime.now().strftime("%Y-%m-%d")
