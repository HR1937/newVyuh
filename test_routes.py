#!/usr/bin/env python3

import requests
import json
from datetime import datetime

# Real API key
RAILRADAR_API_KEY = "rr_live_ccW7ci-7ty2l8DR_yceDZjpJf9PaIPKg"

def test_popular_routes():
    """Test popular train routes that should have active trains"""
    
    print("🚂 Testing Popular Train Routes for Live Data...")
    
    # Popular routes with frequent trains
    routes = [
        ("NDLS", "AGC", "New Delhi to Agra Cantt"),
        ("NDLS", "JP", "New Delhi to Jaipur"),
        ("CSMT", "PUNE", "Mumbai CST to Pune"),
        ("HWH", "SDAH", "Howrah to Sealdah"),
        ("MAS", "CBE", "Chennai Central to Coimbatore"),
        ("NDLS", "LKO", "New Delhi to Lucknow"),
        ("BCT", "ADI", "Mumbai Central to Ahmedabad"),
    ]
    
    headers = {"x-api-key": RAILRADAR_API_KEY}
    base_url = "https://railradar.in/api/v1"
    
    for from_code, to_code, description in routes:
        try:
            url = f"{base_url}/trains/between"
            params = {"from": from_code, "to": to_code}
            
            print(f"\n🔍 Testing route: {description} ({from_code} → {to_code})")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("data", {}).get("trains"):
                    trains = data["data"]["trains"]
                    print(f"    ✅ SUCCESS! Found {len(trains)} trains")
                    
                    # Show first few trains
                    for i, train in enumerate(trains[:3]):
                        train_num = train.get("number", "Unknown")
                        train_name = train.get("name", "Unknown")
                        print(f"      🚂 {train_num}: {train_name}")
                    
                    return from_code, to_code, trains
                else:
                    total_trains = data.get("data", {}).get("totalTrains", 0)
                    print(f"    ⚠️  No active trains found (total: {total_trains})")
            else:
                print(f"    ❌ {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"    💥 Exception: {e}")
    
    return None, None, []

def test_live_train_status():
    """Test live status of specific trains"""
    
    print("\n🔴 Testing Live Train Status...")
    
    # Popular trains that run daily
    trains = [
        "12002",  # Shatabdi Express
        "12951",  # Mumbai Rajdhani  
        "12301",  # Howrah Rajdhani
        "12009",  # Shatabdi Express
        "12023",  # Janshatabdi Express
    ]
    
    headers = {"x-api-key": RAILRADAR_API_KEY}
    base_url = "https://railradar.in/api/v1"
    
    for train_num in trains:
        try:
            url = f"{base_url}/trains/{train_num}"
            params = {
                "journeyDate": datetime.now().strftime("%Y-%m-%d"),
                "dataType": "live"
            }
            
            print(f"  🔍 Testing train {train_num}...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success") and data.get("data"):
                    train_data = data["data"]
                    current_loc = train_data.get("currentLocation", {})
                    status = current_loc.get("status", "Unknown")
                    station = current_loc.get("stationCode", "Unknown")
                    
                    print(f"    ✅ Live data available!")
                    print(f"      Status: {status}")
                    print(f"      Current Station: {station}")
                    
                    return train_num, train_data
                else:
                    print(f"    ⚠️  No live data available")
            else:
                print(f"    ❌ {response.status_code}")
                
        except Exception as e:
            print(f"    💥 Exception: {e}")
    
    return None, None

if __name__ == "__main__":
    print("🚂 VyuhMitra - Route & Live Data Testing")
    print("=" * 60)
    
    # Test routes
    from_station, to_station, trains = test_popular_routes()
    
    if trains:
        print(f"\n🎉 FOUND ACTIVE ROUTE: {from_station} → {to_station}")
        print(f"Available trains: {len(trains)}")
    
    # Test live status
    live_train, live_data = test_live_train_status()
    
    if live_train:
        print(f"\n🔴 FOUND LIVE TRAIN: {live_train}")
        print("Live tracking is working!")
    
    print(f"\n✅ API Testing Complete!")
