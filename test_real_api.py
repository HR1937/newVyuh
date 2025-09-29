#!/usr/bin/env python3

import requests
import json
from datetime import datetime

# Real API key from text.py
RAILRADAR_API_KEY = "rr_live_ccW7ci-7ty2l8DR_yceDZjpJf9PaIPKg"

def test_railradar_api():
    """Test RailRadar API with different endpoints and authentication methods"""
    
    print("🔍 Testing RailRadar API Authentication...")
    print(f"API Key: {RAILRADAR_API_KEY[:20]}...")
    
    base_url = "https://railradar.in/api/v1"
    
    # Test different authentication methods
    auth_methods = [
        {"x-api-key": RAILRADAR_API_KEY},
        {"Authorization": f"Bearer {RAILRADAR_API_KEY}"},
        {"Authorization": f"API-Key {RAILRADAR_API_KEY}"},
        {"api-key": RAILRADAR_API_KEY},
        {"X-API-KEY": RAILRADAR_API_KEY},
    ]
    
    # Test endpoints
    endpoints = [
        ("trains/between", {"from": "NDLS", "to": "BCT"}),
        ("trains/12002", {"journeyDate": datetime.now().strftime("%Y-%m-%d")}),
        ("stations/NDLS/live", {"hours": "2"}),
    ]
    
    for i, headers in enumerate(auth_methods):
        print(f"\n🔐 Testing authentication method {i+1}: {list(headers.keys())[0]}")
        
        for endpoint, params in endpoints:
            url = f"{base_url}/{endpoint}"
            
            try:
                print(f"  📡 Testing: {endpoint}")
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                print(f"    Status: {response.status_code}")
                print(f"    Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"    ✅ SUCCESS! Data keys: {list(data.keys()) if isinstance(data, dict) else 'List with ' + str(len(data)) + ' items'}")
                    
                    # If we found working auth, test more endpoints
                    if endpoint == "trains/between":
                        print(f"    🚂 Found trains data structure:")
                        if isinstance(data, dict):
                            for key, value in data.items():
                                if isinstance(value, list):
                                    print(f"      {key}: {len(value)} items")
                                else:
                                    print(f"      {key}: {type(value).__name__}")
                        
                        return headers, data  # Return working auth method
                        
                elif response.status_code == 401:
                    print(f"    ❌ 401 Unauthorized")
                elif response.status_code == 429:
                    print(f"    ⏳ 429 Rate Limited")
                else:
                    print(f"    ❌ Error: {response.text[:100]}")
                    
            except Exception as e:
                print(f"    💥 Exception: {e}")
    
    return None, None

def test_specific_trains():
    """Test specific train numbers that should exist"""
    
    print("\n🚂 Testing specific train numbers...")
    
    # Popular trains that should have data
    test_trains = [
        "12002",  # Shatabdi Express
        "12951",  # Mumbai Rajdhani
        "12301",  # Howrah Rajdhani
        "11055",  # Godan Express
        "12009",  # Shatabdi Express
    ]
    
    headers = {"x-api-key": RAILRADAR_API_KEY}
    base_url = "https://railradar.in/api/v1"
    
    for train_num in test_trains:
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
                print(f"    ✅ SUCCESS! Keys: {list(data.keys()) if isinstance(data, dict) else 'List'}")
                return train_num, data
            else:
                print(f"    ❌ {response.status_code}: {response.text[:50]}")
                
        except Exception as e:
            print(f"    💥 Exception: {e}")
    
    return None, None

if __name__ == "__main__":
    print("🚂 VyuhMitra - Real API Testing")
    print("=" * 50)
    
    # Test authentication
    working_auth, sample_data = test_railradar_api()
    
    if working_auth:
        print(f"\n🎉 FOUND WORKING AUTHENTICATION!")
        print(f"Working headers: {working_auth}")
        print(f"Sample data structure: {json.dumps(sample_data, indent=2)[:500]}...")
    else:
        print(f"\n❌ No working authentication found")
        
    # Test specific trains
    working_train, train_data = test_specific_trains()
    
    if working_train:
        print(f"\n🚂 FOUND WORKING TRAIN: {working_train}")
        print(f"Train data: {json.dumps(train_data, indent=2)[:500]}...")
