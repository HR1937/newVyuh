#!/usr/bin/env python3

import requests
import json

def debug_railradar_response():
    """Debug the exact RailRadar API response format"""
    
    api_key = "rr_live_ccW7ci-7ty2l8DR_yceDZjpJf9PaIPKg"
    base_url = "https://railradar.in/api/v1"
    headers = {"x-api-key": api_key}
    
    print("🔍 Debugging RailRadar API response format...")
    
    try:
        response = requests.get(f"{base_url}/trains/between", 
                              params={"from": "NDLS", "to": "AGC"}, 
                              headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n📋 FULL API RESPONSE:")
            print(json.dumps(data, indent=2))
            
            print(f"\n🔍 RESPONSE ANALYSIS:")
            print(f"Response type: {type(data)}")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if isinstance(data, dict) and "data" in data:
                trains = data["data"]
                print(f"Trains array length: {len(trains) if isinstance(trains, list) else 'Not a list'}")
                
                if isinstance(trains, list) and len(trains) > 0:
                    print(f"\n🚂 FIRST TRAIN SAMPLE:")
                    print(json.dumps(trains[0], indent=2))
                    print(f"\nFirst train keys: {list(trains[0].keys()) if isinstance(trains[0], dict) else 'Not a dict'}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")

if __name__ == "__main__":
    debug_railradar_response()
