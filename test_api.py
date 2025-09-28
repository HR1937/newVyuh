#!/usr/bin/env python3
"""
Quick test script to verify RailRadar API integration
"""

import sys
import os
sys.path.append('backend')

from backend.data_collector import RailRadarDataCollector
from backend.config import Config

def test_api_connection():
    """Test the VyuhMitra system with demo data"""
    config = Config()
    collector = RailRadarDataCollector(config.RAILRADAR_API_KEY)
    
    print("🚂 Testing VyuhMitra System with Demo Data...")
    print(f"Section: {config.DEFAULT_FROM_STATION} to {config.DEFAULT_TO_STATION}")
    
    try:
        # Test section data collection (will use demo data)
        print(f"\n🚊 Testing section data collection...")
        section_data = collector.collect_section_data(config.DEFAULT_FROM_STATION, config.DEFAULT_TO_STATION)
        
        if section_data:
            print("✅ Section data collected successfully!")
            print(f"   Total trains: {section_data.get('total_trains', 0)}")
            print(f"   Valid schedules: {section_data.get('valid_schedules', 0)}")
            print(f"   Live data entries: {section_data.get('live_entry_count', 0)}")
            print(f"   Abnormalities: {len(section_data.get('abnormalities', []))}")
            print(f"   Data source: {section_data.get('data_source', 'unknown')}")
            
            # Show train details
            static_schedules = section_data.get('static_schedules', {})
            if static_schedules:
                print(f"\n🚆 Train Schedule Details:")
                for train_id, schedule in static_schedules.items():
                    train_name = schedule.get('train_name', 'Unknown')
                    entry_time = schedule.get('entry_time', 0)
                    entry_hour = entry_time // 60
                    entry_min = entry_time % 60
                    print(f"   - {train_id}: {train_name} (Entry: {entry_hour:02d}:{entry_min:02d})")
            
            # Show live data details
            live_data = section_data.get('live_data', {})
            if live_data:
                print(f"\n📍 Live Train Status:")
                for train_id, live_info in live_data.items():
                    delay = live_info.get('overallDelayMinutes', 0)
                    status = live_info.get('statusSummary', 'Unknown')
                    current_status = live_info.get('currentLocation', {}).get('status', 'Unknown')
                    print(f"   - {train_id}: {status} (Delay: {delay}min, Status: {current_status})")
            
            # Show abnormalities
            abnormalities = section_data.get('abnormalities', [])
            if abnormalities:
                print(f"\n🚨 Abnormalities Detected:")
                for ab in abnormalities:
                    train_id = ab.get('train_id', 'Unknown')
                    ab_type = ab.get('abnormality_type', 'Unknown')
                    delay = ab.get('delay_minutes', 0)
                    severity = ab.get('severity', 'Unknown')
                    description = ab.get('description', 'No description')
                    print(f"   - Train {train_id}: {ab_type} ({severity} severity, {delay}min delay)")
                    print(f"     {description}")
        else:
            print("❌ Failed to collect section data")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_api_connection()
    if success:
        print("\n🎉 API test completed successfully!")
    else:
        print("\n💥 API test failed!")
        sys.exit(1)
