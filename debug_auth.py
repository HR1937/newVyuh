#!/usr/bin/env python3
"""
Debug RailRadar API authentication issues
"""
import requests
import json

# Your API key from logs
API_KEY = "rr_live_QFVeOcFaAuBVtWNlpF9_oXuKVeBNo2m8"

def test_different_auth_methods():
    """Test different ways to send the API key"""
    
    base_url = "https://railradar.in/api/v1"
    
    # Test endpoints in order of complexity
    test_cases = [
        {
            "name": "Simple stations endpoint",
            "url": f"{base_url}/stations/NDLS/info",
            "params": None
        },
        {
            "name": "Trains between stations", 
            "url": f"{base_url}/trains/between",
            "params": {"from": "NDLS", "to": "BCT"}
        }
    ]
    
    # Different header formats to try
    auth_methods = [
        {"x-api-key": API_KEY},
        {"X-API-Key": API_KEY},
        {"Authorization": f"Bearer {API_KEY}"},
        {"Authorization": f"ApiKey {API_KEY}"},
        {"api-key": API_KEY},
        {"X-RapidAPI-Key": API_KEY}
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"URL: {test_case['url']}")
        
        for i, headers in enumerate(auth_methods):
            print(f"\n  Method {i+1}: {headers}")
            
            try:
                if test_case['params']:
                    response = requests.get(test_case['url'], headers=headers, params=test_case['params'], timeout=5)
                else:
                    response = requests.get(test_case['url'], headers=headers, timeout=5)
                
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("    ✅ SUCCESS! This auth method works")
                    try:
                        data = response.json()
                        print(f"    Response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    except:
                        print(f"    Response length: {len(response.text)}")
                    return headers  # Return working method
                elif response.status_code == 401:
                    print("    ❌ 401 Unauthorized")
                elif response.status_code == 429:
                    print("    ⚠️ 429 Rate Limited")
                else:
                    print(f"    ❓ {response.status_code}: {response.text[:100]}")
                    
            except Exception as e:
                print(f"    💥 Error: {e}")
        
        print(f"  All auth methods failed for {test_case['name']}")
    
    return None

def test_account_status():
    """Test if account/key is active with minimal request"""
    print(f"\n🔍 Testing account status...")
    print(f"API Key: {API_KEY}")
    
    # Try the simplest possible endpoint
    url = "https://railradar.in/api/v1/stations/all-kvs"
    headers = {"x-api-key": API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if 'x-requests-remaining' in response.headers:
            print(f"Requests remaining: {response.headers['x-requests-remaining']}")
        
        if response.status_code == 401:
            print("\n❌ Account Issues Detected:")
            print("1. API key might be deactivated")
            print("2. Account might need email verification") 
            print("3. Account might be suspended")
            print("\n🔧 Solutions:")
            print("1. Login to https://railradar.in/dashboard")
            print("2. Check account status and verify email")
            print("3. Generate a new API key")
            print("4. Contact support if needed")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    print("🚂 RailRadar API Authentication Debug")
    print("=" * 50)
    
    # Test account status first
    if test_account_status():
        print("\n✅ Account is active!")
    else:
        print("\n❌ Account/Key issues detected")
    
    # Test different auth methods
    working_method = test_different_auth_methods()
    
    if working_method:
        print(f"\n🎉 Working authentication method found: {working_method}")
    else:
        print(f"\n💔 No working authentication method found")
        print("Your API key appears to be invalid or your account needs attention")
