#!/usr/bin/env python3
"""
Test which RailRadar endpoints work with your API key
"""
import requests

API_KEY = "rr_live_QFVeOcFaAuBVtWNlpF9_oXuKVeBNo2m8"

def test_endpoint(name, url, params=None):
    """Test a single endpoint"""
    headers = {"x-api-key": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        status = "✅ WORKS" if response.status_code == 200 else f"❌ {response.status_code}"
        
        # Get remaining requests from headers
        remaining = response.headers.get('x-requests-remaining', 'N/A')
        
        print(f"{status} | {name} | Remaining: {remaining}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"      Keys: {list(data.keys())}")
                elif isinstance(data, list):
                    print(f"      Array length: {len(data)}")
            except:
                pass
        elif response.status_code == 401:
            print(f"      Error: Unauthorized - endpoint not available in your plan")
        elif response.status_code == 429:
            print(f"      Error: Rate limited")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ ERROR | {name} | {e}")
        return False

def main():
    print("🚂 Testing RailRadar API Endpoints")
    print("=" * 60)
    
    # Test various endpoints to see what's available
    endpoints = [
        ("Station Info", "https://railradar.in/api/v1/stations/NDLS/info"),
        ("All Stations KV", "https://railradar.in/api/v1/stations/all-kvs"),
        ("All Trains KV", "https://railradar.in/api/v1/trains/all-kvs"),
        ("Trains Between", "https://railradar.in/api/v1/trains/between", {"from": "NDLS", "to": "BCT"}),
        ("Train Details", "https://railradar.in/api/v1/trains/12951"),
        ("Train Schedule", "https://railradar.in/api/v1/trains/12951/schedule", {"journeyDate": "2025-09-29"}),
        ("Train Instances", "https://railradar.in/api/v1/trains/12951/instances"),
        ("Station Live Board", "https://railradar.in/api/v1/stations/NDLS/live"),
        ("Search Trains", "https://railradar.in/api/v1/search/trains", {"q": "rajdhani"}),
        ("Search Stations", "https://railradar.in/api/v1/search/stations", {"q": "delhi"}),
    ]
    
    working_endpoints = []
    
    for endpoint_data in endpoints:
        name = endpoint_data[0]
        url = endpoint_data[1]
        params = endpoint_data[2] if len(endpoint_data) > 2 else None
        
        if test_endpoint(name, url, params):
            working_endpoints.append(name)
        print()
    
    print("=" * 60)
    print(f"✅ Working endpoints ({len(working_endpoints)}):")
    for endpoint in working_endpoints:
        print(f"   - {endpoint}")
    
    if "Trains Between" not in working_endpoints:
        print("\n❌ CRITICAL: 'trains/between' endpoint not available!")
        print("This is the main endpoint VyuhMitra needs for live data.")
        print("\n🔧 Solutions:")
        print("1. Upgrade your RailRadar plan to access trains/between")
        print("2. Use alternative endpoints like station live boards")
        print("3. Contact RailRadar support about endpoint access")
        
        # Suggest alternative approach
        if "Station Live Board" in working_endpoints:
            print("\n💡 Alternative: Use station live boards to build train data")
            print("   We can modify VyuhMitra to use /stations/{code}/live instead")

if __name__ == "__main__":
    main()
