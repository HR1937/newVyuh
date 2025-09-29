#!/usr/bin/env python3
"""
Quick test script to verify RailRadar API key validity
"""
import requests

# Your current API key from the logs
API_KEY = "rr_live_QFVeOcFaAuBVtWNlpF9_oXuKVeBNo2m8"

def test_api_key():
    """Test if the API key works with a simple endpoint"""
    
    # Test with a simple endpoint first
    url = "https://railradar.in/api/v1/trains/between"
    headers = {"x-api-key": API_KEY}
    params = {"from": "NDLS", "to": "BCT"}  # Delhi to Mumbai - should have trains
    
    print(f"Testing API key: {API_KEY[:20]}...")
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Key is VALID!")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            if isinstance(data, dict) and 'trains' in data:
                print(f"Found {len(data['trains'])} trains")
        elif response.status_code == 401:
            print("❌ API Key is INVALID or EXPIRED")
            print("Get a new key from: https://railradar.in/dashboard")
        elif response.status_code == 429:
            print("⚠️ Rate limited - too many requests")
        else:
            print(f"❓ Unexpected status: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_api_key()
