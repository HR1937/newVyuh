#!/usr/bin/env python3

import requests
import json

def test_dashboard_endpoints():
    """Test the dashboard API endpoints directly"""
    
    base_url = "http://127.0.0.1:5000"
    
    endpoints = [
        "/api/dashboard/summary",
        "/api/section/current", 
        "/api/trains/schedule",
        "/api/kpi/current",
        "/api/abnormalities"
    ]
    
    print("🔍 Testing Dashboard API Endpoints...")
    
    for endpoint in endpoints:
        try:
            print(f"\n📡 Testing: {endpoint}")
            url = f"{base_url}{endpoint}"
            
            response = requests.get(url, timeout=30)
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    print(f"  ✅ SUCCESS!")
                    
                    # Show key data
                    if "data" in data:
                        data_content = data["data"]
                        if isinstance(data_content, dict):
                            print(f"  📊 Data keys: {list(data_content.keys())[:5]}")
                            
                            # Show specific info for different endpoints
                            if "section" in data_content:
                                print(f"  🚉 Section: {data_content.get('section')}")
                                print(f"  🚂 Trains: {data_content.get('valid_schedules', 0)}")
                                print(f"  📡 Data source: {data_content.get('data_source')}")
                        else:
                            print(f"  📊 Data type: {type(data_content).__name__}")
                else:
                    print(f"  ❌ API returned success=false: {data.get('error', 'Unknown error')}")
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            print(f"  ⏰ TIMEOUT - API taking too long (>30s)")
        except Exception as e:
            print(f"  💥 Exception: {e}")

if __name__ == "__main__":
    test_dashboard_endpoints()
