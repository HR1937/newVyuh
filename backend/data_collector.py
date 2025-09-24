import os

import requests
import json
import time
import requests
from requests.exceptions import HTTPError
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

class RailRadarDataCollector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 120  # 2 minutes in seconds


    def _setup_logger(self):
        logger = logging.getLogger('DataCollector')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[DATA] %(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def fetch_section_trains(self, from_station, to_station):
        cache_key = f"trains_{from_station}_{to_station}"
        current_time = time.time()

        # Return cached data if within 2 mins
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if current_time - timestamp < self.min_request_interval:
                return cached_data

        # Wait to respect min_request_interval
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            time.sleep(wait_time)

        url = f"https://railradar.in/api/v1/trains/between?from={from_station}&to={to_station}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()

            # Cache results
            self.cache[cache_key] = (data, time.time())
            self.last_request_time = time.time()

            return data
        except HTTPError as e:
            print(f"HTTP error: {e}")
            if cache_key in self.cache:
                print("Using cached data due to HTTP error")
                return self.cache[cache_key][0]
            else:
                raise
        except Exception as e:
            print(f"Other error: {e}")
            if cache_key in self.cache:
                print("Using cached data due to error")
                return self.cache[cache_key][0]
            else:
                raise

    def fetch_train_live_status(self, train_number: str, journey_date: str = None) -> Dict:
        """Get real-time live status of a train"""
        if not journey_date:
            journey_date = datetime.now().strftime("%Y-%m-%d")

        url = f"{self.base_url}/trains/{train_number}"
        params = {
            "dataType": "live",
            "journeyDate": journey_date
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("success") and data.get("data", {}).get("liveData"):
                live_data = data["data"]["liveData"]
                self.logger.info(f"✅ Live data retrieved for train {train_number}")
                return live_data
            else:
                self.logger.warning(f"No live data for train {train_number} on {journey_date}")
                return {}

        except Exception as e:
            self.logger.error(f"Error fetching live status for {train_number}: {e}")
            return {}

    def fetch_train_schedule(self, train_number: str, journey_date: str = None) -> Dict:
        """Get static schedule for a train"""
        if not journey_date:
            journey_date = datetime.now().strftime("%Y-%m-%d")

        url = f"{self.base_url}/trains/{train_number}/schedule"
        params = {"journeyDate": journey_date}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                schedule_data = data.get("data", {})
                self.logger.info(f"✅ Schedule retrieved for train {train_number}")
                return schedule_data
            else:
                self.logger.warning(f"No schedule data for train {train_number}")
                return {}

        except Exception as e:
            self.logger.error(f"Error fetching schedule for {train_number}: {e}")
            return {}

    def fetch_train_instances(self, train_number: str) -> List[Dict]:
        """Get running instances of a train to find active journey dates"""
        url = f"{self.base_url}/trains/{train_number}/instances"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()

            if data.get("success"):
                instances = data.get("data", [])
                running_instances = [inst for inst in instances if inst.get("status") == "RUNNING"]
                self.logger.info(f"Found {len(running_instances)} running instances for {train_number}")
                return running_instances
            return []

        except Exception as e:
            self.logger.error(f"Error fetching instances for {train_number}: {e}")
            return []

    def get_running_journey_date(self, train_number: str) -> Optional[str]:
        """Find the active journey date for a running train"""
        instances = self.fetch_train_instances(train_number)

        for instance in instances:
            if instance.get("status") == "RUNNING" and instance.get("startDate"):
                return instance["startDate"]

        # Fallback: try today and yesterday
        for days_back in [0, 1]:
            test_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            live_data = self.fetch_train_live_status(train_number, test_date)
            if live_data:
                return test_date

        return None

    def detect_abnormalities(self, static_schedules: Dict, section: str) -> List[Dict]:
        """Compare static schedules with live data to detect abnormalities"""
        abnormalities = []

        for train_id, static_data in static_schedules.items():
            # Get live data for this train
            journey_date = self.get_running_journey_date(train_id)
            if not journey_date:
                continue

            live_data = self.fetch_train_live_status(train_id, journey_date)
            if not live_data:
                continue

            # Check for delays and stoppages
            overall_delay = live_data.get("overallDelayMinutes", 0)
            current_location = live_data.get("currentLocation", {})
            status_summary = live_data.get("statusSummary", "")

            # Abnormality conditions based on your requirements
            is_delayed = abs(overall_delay) >= 10  # 10+ minute delay
            is_stopped = "stopped" in status_summary.lower() and abs(overall_delay) >= 5

            if is_delayed or is_stopped:
                abnormality = {
                    "train_id": train_id,
                    "journey_date": journey_date,
                    "section": section,
                    "delay_minutes": overall_delay,
                    "status": status_summary,
                    "location": current_location.get("stationCode", "Unknown"),
                    "location_name": current_location.get("stationName", "Unknown"),
                    "abnormality_type": "delay" if is_delayed else "stoppage",
                    "detected_at": datetime.now().isoformat(),
                    "severity": "high" if abs(overall_delay) > 30 else "medium"
                }
                abnormalities.append(abnormality)

        self.logger.info(f"Detected {len(abnormalities)} abnormalities in section {section}")
        return abnormalities

    def collect_section_data(self, from_station: str, to_station: str) -> Dict:
        """Comprehensive data collection for a railway section"""
        self.logger.info(f"Collecting data for section {from_station}-{to_station}")

        # Get trains running in this section
        section_trains = self.fetch_section_trains(from_station, to_station)

        if not section_trains:
            return {
                "section": f"{from_station}-{to_station}",
                "timestamp": datetime.now().isoformat(),
                "total_trains": 0,
                "valid_schedules": 0,
                "static_schedules": {},
                "live_data": {},
                "abnormalities": [],
                "message": "No trains found for this section"
            }

        static_schedules = {}
        live_data = {}

        # Process each train
        for train in section_trains:
            train_number = train.get("trainNumber")
            if not train_number:
                continue

            # Get static schedule
            journey_date = self.get_running_journey_date(train_number) or datetime.now().strftime("%Y-%m-%d")
            schedule_data = self.fetch_train_schedule(train_number, journey_date)

            if schedule_data and schedule_data.get("route"):
                # Extract section-specific schedule
                route = schedule_data["route"]
                entry_stop = next((s for s in route if s.get("station", {}).get("code") == from_station), None)
                exit_stop = next((s for s in route if s.get("station", {}).get("code") == to_station), None)

                if entry_stop and exit_stop:
                    static_schedules[train_number] = {
                        "train_name": schedule_data.get("train", {}).get("name", ""),
                        "entry_time": self._parse_time_to_minutes(entry_stop.get("schedule", {}).get("departure")),
                        "exit_time": self._parse_time_to_minutes(exit_stop.get("schedule", {}).get("arrival")),
                        "distance": exit_stop.get("distanceKilometers", 0) - entry_stop.get("distanceKilometers", 0),
                        "entry_platform": entry_stop.get("schedule", {}).get("platform"),
                        "exit_platform": exit_stop.get("schedule", {}).get("platform"),
                        "journey_date": journey_date
                    }

                    # Get live data
                    live_status = self.fetch_train_live_status(train_number, journey_date)
                    if live_status:
                        live_data[train_number] = live_status

        # Detect abnormalities
        abnormalities = self.detect_abnormalities(static_schedules, f"{from_station}-{to_station}")

        result = {
            "section": f"{from_station}-{to_station}",
            "timestamp": datetime.now().isoformat(),
            "total_trains": len(section_trains),
            "valid_schedules": len(static_schedules),
            "static_schedules": static_schedules,
            "live_data": live_data,
            "abnormalities": abnormalities,
            "data_quality": {
                "schedule_coverage": len(static_schedules) / len(section_trains) if section_trains else 0,
                "live_data_coverage": len(live_data) / len(static_schedules) if static_schedules else 0
            }
        }

        self.logger.info(f"Section data collected: {len(static_schedules)} schedules, {len(live_data)} live, {len(abnormalities)} abnormalities")
        return result

    def _parse_time_to_minutes(self, time_val) -> Optional[int]:
        """Parse time string to minutes from midnight"""
        if time_val is None:
            return None
        if isinstance(time_val, int):
            return time_val
        if isinstance(time_val, str):
            try:
                if ":" in time_val:
                    parts = time_val.split(":")
                    if len(parts) >= 2:
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        return hours * 60 + minutes
            except:
                pass
        return None

    def load_static_schedule_file(self, filepath: str = "data.jio") -> Dict:
        """Load static schedule data from data.jio file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.logger.info(f"Loaded static schedule data from {filepath}")
            return data
        except Exception as e:
            self.logger.error(f"Error loading {filepath}: {e}")
            return {}

    def save_section_data(self, section_data: Dict, filepath: str = None) -> str:
        """Save section data to file"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            section_name = section_data.get("section", "unknown").replace("-", "_")
            filepath = f"data/live/section_{section_name}_{timestamp}.json"

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(section_data, f, indent=2)
            self.logger.info(f"Section data saved to {filepath}")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving section data: {e}")
            return ""
