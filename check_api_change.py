#!/usr/bin/env python3
"""
Check what changed with RailRadar API access
"""
import requests
import time

API_KEY = "rr_live_QFVeOcFaAuBVtWNlpF9_oXuKVeBNo2m8"

def test_trains_between():
    """Test the exact same endpoint that was working before"""
    url = "https://railradar.in/api/v1/trains/between"
    headers = {"x-api-key": API_KEY}
    params = {"from": "GY", "to": "GTL"}  # Same params from your logs
    
    print(f"🧪 Testing exact same request from your logs:")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")
    print()
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['x-requests-remaining', 'x-user-id', 'date', 'cf-ray']:
                print(f"  {key}: {value}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! API is working again")
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"Response structure: {list(data.keys())}")
                    if 'trains' in data:
                        print(f"Found {len(data['trains'])} trains")
                        if data['trains']:
                            train = data['trains'][0]
                            print(f"Sample train keys: {list(train.keys())}")
            except Exception as e:
                print(f"JSON parse error: {e}")
                
        elif response.status_code == 401:
            print("\n❌ Still getting 401 Unauthorized")
            print("Possible causes:")
            print("1. API key was temporarily suspended")
            print("2. Rate limiting triggered temporary block")
            print("3. Account verification required")
            print("4. RailRadar changed authentication requirements")
            
        else:
            print(f"\n❓ Unexpected status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def check_account_status():
    """Check if basic endpoints still work"""
    print("\n🔍 Checking account status with basic endpoints:")
    
    basic_endpoints = [
        ("All Stations", "https://railradar.in/api/v1/stations/all-kvs"),
        ("All Trains", "https://railradar.in/api/v1/trains/all-kvs")
    ]
    
    for name, url in basic_endpoints:
        try:
            response = requests.get(url, headers={"x-api-key": API_KEY}, timeout=5)
            status = "✅" if response.status_code == 200 else f"❌ {response.status_code}"
            remaining = response.headers.get('x-requests-remaining', 'N/A')
            print(f"{status} {name} | Remaining: {remaining}")
        except Exception as e:
            print(f"❌ {name} | Error: {e}")

def suggest_solutions():
    """Suggest what to do next"""
    print("\n🔧 Next Steps:")
    print("1. Wait 5-10 minutes and try again (temporary rate limit)")
    print("2. Check your RailRadar dashboard for account notifications")
    print("3. Try generating a new API key")
    print("4. Contact RailRadar support if issue persists")
    print("\n💡 Immediate workaround:")
    print("Set ENABLE_DEMO=1 to use demo data while debugging API issues")

if __name__ == "__main__":
    print("🚂 RailRadar API Status Check")
    print("=" * 50)
    
    # Check basic account status first
    check_account_status()
    
    # Test the problematic endpoint
    test_trains_between()
    
    # Provide solutions
    suggest_solutions()
