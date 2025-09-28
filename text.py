import requests
from flask import Flask, jsonify, render_template_string
from datetime import datetime
import time
import json

app = Flask(__name__)

API_KEY = "rr_live_-sfYzdZsdnVJkwmY3_O3--_t-om3a1lc"

TRAINS_ARRAY = {
  "count": 32,
  "trains": [
    {
      "name": "Karaikal - Mumbai LTT Weekly Express (PT)",
      "number": "11018",
      "type": "Mail/Express"
    }
  ]
}

def make_api_request(train_number):
    """Make API request to the main train endpoint with proper parameters"""
    try:
        # Use current date
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        url = f"https://railradar.in/api/v1/trains/{train_number}"
        
        headers = {
            "x-api-key": API_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://railradar.in/",
            "Origin": "https://railradar.in"
        }
        
        params = {
            "journeyDate": current_date,
            "dataType": "full",
            "provider": "railradar",
            "userId": ""
        }
        
        print(f"\n🔍 Fetching {train_number} for date {current_date}")
        print(f"📤 URL: {url}")
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success for {train_number}")
            
            # PRINT COMPLETE RESPONSE IN JSON FORMAT
            print(f"\n🎯 COMPLETE API RESPONSE FOR {train_number}:")
            print("=" * 80)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("=" * 80)
            
            return data
        else:
            print(f"❌ API Error {response.status_code} for {train_number}")
            print(f"📄 Response text: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout for {train_number}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"🔌 Connection error for {train_number}")
        return None
    except Exception as e:
        print(f"💥 Request failed for {train_number}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def safe_get(data, keys, default="N/A"):
    """Safely get nested dictionary values"""
    try:
        if isinstance(keys, str):
            return data.get(keys, default)
        
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current if current is not None and current != "" else default
    except:
        return default

def extract_train_data(api_response, train_info):
    """Extract train data from the main API response"""
    if not api_response:
        return {
            "train_name": train_info["name"],
            "train_number": train_info["number"],
            "train_type": train_info["type"],
            "status": "API_REQUEST_FAILED",
            "error": "Could not fetch data from API",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "api_response_available": False
        }
    
    try:
        # Start with basic train info
        train_data = {
            "train_name": train_info["name"],
            "train_number": train_info["number"],
            "train_type": train_info["type"],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "api_response_available": True
        }
        
        print(f"\n📊 EXTRACTING DATA FROM RESPONSE FOR {train_info['number']}:")
        print("-" * 50)
        
        # Extract train static information
        train_static = safe_get(api_response, "train", {})
        print(f"📋 Train static data available: {bool(train_static)}")
        
        train_data["train_number_api"] = safe_get(train_static, "trainNumber")
        train_data["train_name_api"] = safe_get(train_static, "trainName")
        train_data["source_station"] = safe_get(train_static, "sourceStationName")
        train_data["destination_station"] = safe_get(train_static, "destinationStationName")
        train_data["train_type_api"] = safe_get(train_static, "type")
        train_data["zone"] = safe_get(train_static, "zone")
        train_data["distance_km"] = safe_get(train_static, "distanceKm", 0)
        train_data["travel_time_minutes"] = safe_get(train_static, "travelTimeMinutes", 0)
        train_data["avg_speed_kmph"] = safe_get(train_static, "avgSpeedKmph", 0)
        train_data["total_halts"] = safe_get(train_static, "totalHalts", 0)
        
        # Extract live data
        live_data = safe_get(api_response, "liveData", {})
        print(f"📡 Live data available: {bool(live_data)}")
        
        train_data["train_delay"] = safe_get(live_data, "overallDelayMinutes", 0)
        train_data["status_summary"] = safe_get(live_data, "statusSummary", "")
        train_data["last_updated_at"] = safe_get(live_data, "lastUpdatedAt", "")
        
        # Extract current location
        current_location = safe_get(live_data, "currentLocation", {})
        print(f"📍 Current location data: {bool(current_location)}")
        
        train_data["live_lat"] = safe_get(current_location, "latitude")
        train_data["live_lng"] = safe_get(current_location, "longitude")
        train_data["current_station_code"] = safe_get(current_location, "stationCode")
        train_data["current_location_status"] = safe_get(current_location, "status")
        train_data["distance_from_origin_km"] = safe_get(current_location, "distanceFromOriginKm", 0)
        
        # Process live route for station information
        live_route = safe_get(live_data, "route", [])
        print(f"🛤 Live route stations: {len(live_route) if isinstance(live_route, list) else 0}")
        
        if live_route and isinstance(live_route, list):
            train_data["total_stations"] = len(live_route)
            
            # Find completed and upcoming stations
            completed_stations = 0
            next_station = None
            current_station = None
            
            for i, station_data in enumerate(live_route):
                if not isinstance(station_data, dict):
                    continue
                    
                actual_arrival = station_data.get("actualArrival")
                actual_departure = station_data.get("actualDeparture")
                
                # Count completed stations (has actual arrival)
                if actual_arrival is not None:
                    completed_stations += 1
                    current_station = station_data
                else:
                    # First station without actual arrival is the next station
                    if next_station is None:
                        next_station = station_data
                        train_data["next_station_sequence"] = i + 1
            
            train_data["completed_stations"] = completed_stations
            train_data["remaining_stations"] = len(live_route) - completed_stations
            
            # Set current station info
            if current_station:
                station_info = safe_get(current_station, "station", {})
                train_data["current_station_name"] = safe_get(station_info, "name", "Unknown")
                train_data["current_station_code"] = safe_get(station_info, "code", train_data.get("current_station_code", "Unknown"))
                train_data["current_station_delay"] = safe_get(current_station, "delayArrivalMinutes", 0)
            
            # Set next station info
            if next_station:
                station_info = safe_get(next_station, "station", {})
                train_data["next_station_name"] = safe_get(station_info, "name", "Unknown")
                train_data["next_station_code"] = safe_get(station_info, "code", "Unknown")
                train_data["next_station_delay"] = safe_get(next_station, "delayArrivalMinutes", 0)
        else:
            train_data["total_stations"] = 0
            train_data["completed_stations"] = 0
            train_data["remaining_stations"] = 0
        
        # Extract static route information
        static_route = safe_get(api_response, "route", [])
        train_data["static_route_stations"] = len(static_route) if isinstance(static_route, list) else 0
        
        # Extract metadata
        metadata = safe_get(api_response, "metadata", {})
        train_data["has_live_data"] = safe_get(metadata, "hasLiveData", False)
        train_data["last_live_update"] = safe_get(metadata, "lastLiveUpdate", "")
        
        # Add status summary from root level
        train_data["status_summary_global"] = safe_get(api_response, "statusSummary", "")
        
        # Print extracted data for debugging
        print(f"\n📈 EXTRACTED DATA FOR {train_info['number']}:")
        print("-" * 50)
        for key, value in train_data.items():
            if key not in ['train_name', 'train_number', 'train_type', 'last_updated']:
                print(f"  {key}: {value}")
        
        print(f"✅ Successfully processed {train_info['number']}")
        return train_data
        
    except Exception as e:
        print(f"❌ Error processing API data for {train_info['number']}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "train_name": train_info["name"],
            "train_number": train_info["number"],
            "train_type": train_info["type"],
            "status": "DATA_PROCESSING_ERROR",
            "error": str(e),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "api_response_available": False
        }

def get_all_trains_data():
    """Get data for all trains"""
    all_trains_data = []
    successful = 0
    
    print(f"\n🚆 STARTING TO FETCH DATA FOR {len(TRAINS_ARRAY['trains'])} TRAINS")
    print(f"📅 Current date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"🔑 API Key: {API_KEY[:10]}...{API_KEY[-10:]}")
    print("=" * 80)
    
    for i, train in enumerate(TRAINS_ARRAY["trains"], 1):
        print(f"\n" + "=" * 80)
        print(f"[{i}/{len(TRAINS_ARRAY['trains'])}] PROCESSING {train['number']} - {train['name']}")
        print("=" * 80)
        
        api_response = make_api_request(train["number"])
        train_data = extract_train_data(api_response, train)
        
        all_trains_data.append(train_data)
        if train_data.get("api_response_available"):
            successful += 1
            print(f"✅ SUCCESS: Added data for {train['number']}")
        else:
            print(f"❌ FAILED: Only basic info for {train['number']}")
        
        # Rate limiting
        time.sleep(2)
    
    print(f"\n📈 FETCH COMPLETED: {successful}/{len(TRAINS_ARRAY['trains'])} successful")
    
    return {
        "trains": all_trains_data,
        "total_trains": len(TRAINS_ARRAY["trains"]),
        "successful": successful,
        "failed": len(TRAINS_ARRAY["trains"]) - successful,
        "success_rate": f"{(successful/len(TRAINS_ARRAY['trains']))*100:.1f}%",
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# Simple HTML Template for basic display
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Train Data Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .header { text-align: center; margin-bottom: 30px; }
        .stats { display: flex; justify-content: space-around; margin-bottom: 20px; }
        .stat-card { background: #e3f2fd; padding: 15px; border-radius: 8px; text-align: center; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #2196f3; color: white; }
        tr:hover { background: #f5f5f5; }
        .status-on-time { color: green; }
        .status-delayed { color: red; }
        .no-data { color: #999; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚆 Train Data Dashboard</h1>
            <p>Last updated: {{ summary.last_updated }}</p>
            <button onclick="location.reload()">Refresh Data</button>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>Total Trains</h3>
                <div>{{ summary.total_trains }}</div>
            </div>
            <div class="stat-card">
                <h3>Successful</h3>
                <div>{{ summary.successful }}</div>
            </div>
            <div class="stat-card">
                <h3>Failed</h3>
                <div>{{ summary.failed }}</div>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <div>{{ summary.success_rate }}</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Train Number</th>
                    <th>Train Name</th>
                    <th>Status</th>
                    <th>Delay</th>
                    <th>Current Location</th>
                    <th>Route</th>
                </tr>
            </thead>
            <tbody>
                {% for train in summary.trains %}
                <tr>
                    <td>{{ train.train_number }}</td>
                    <td>{{ train.train_name }}</td>
                    <td>
                        {% if train.api_response_available %}
                            {{ train.status_summary or train.status_summary_global or 'Running' }}
                        {% else %}
                            <span class="no-data">No API Data</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if train.api_response_available %}
                            {% if train.train_delay == 0 %}
                                <span class="status-on-time">On Time</span>
                            {% elif train.train_delay > 0 %}
                                <span class="status-delayed">+{{ train.train_delay }} min</span>
                            {% else %}
                                {{ train.train_delay }} min
                            {% endif %}
                        {% else %}
                            <span class="no-data">N/A</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if train.api_response_available %}
                            {{ train.current_station_name or train.current_station_code or 'N/A' }}
                        {% else %}
                            <span class="no-data">N/A</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if train.api_response_available %}
                            {{ train.source_station }} → {{ train.destination_station }}
                        {% else %}
                            <span class="no-data">N/A</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

@app.route("/")
def dashboard():
    """Main dashboard - HTML display"""
    summary = get_all_trains_data()
    return render_template_string(HTML_TEMPLATE, summary=summary)

@app.route("/api/trains")
def api_all_trains():
    """API: Get status of all trains"""
    summary = get_all_trains_data()
    return jsonify(summary)

@app.route("/api/trains/<train_number>")
def api_single_train(train_number):
    """API: Get status of a specific train"""
    train_info = next((t for t in TRAINS_ARRAY["trains"] if t["number"] == train_number), None)
    
    if not train_info:
        return jsonify({"error": "Train not found"}), 404
    
    api_response = make_api_request(train_number)
    train_data = extract_train_data(api_response, train_info)
    
    return jsonify(train_data)

@app.route("/api/debug/<train_number>")
def api_debug_train(train_number):
    """API: Get raw API response for debugging"""
    train_info = next((t for t in TRAINS_ARRAY["trains"] if t["number"] == train_number), None)
    
    if not train_info:
        return jsonify({"error": "Train not found"}), 404
    
    api_response = make_api_request(train_number)
    
    return jsonify({
        "train_info": train_info,
        "api_response": api_response,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == "__main__":
    print("🚀 Starting Train Data Dashboard")
    print("📊 Available at: http://localhost:5000")
    print("🔧 API endpoints:")
    print("   • /api/trains    - JSON data for all trains")
    print("   • /api/trains/<number> - JSON data for single train")
    print("   • /api/debug/<number> - Raw API response for debugging")
    print("\n⚠  DEBUG MODE: Will print complete API responses in terminal")
    print("=" * 80)
    app.run(debug=True, port=5000, host='0.0.0.0')