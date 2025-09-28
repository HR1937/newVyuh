import os

import json
import logging
import time
import requests
from datetime import datetime, timedelta
from requests.exceptions import HTTPError, RequestException
from typing import Dict, List, Optional

from backend.config import Config


class RailRadarDataCollector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})
        self.base_url = "https://railradar.in/api/v1"  # add base url
        self.headers = {"x-api-key": api_key}          # for direct requests when needed
        self.cache = {}
        self.last_request_time = 0
        self.min_request_interval = 120  # 2 minutes in seconds
        self.logger = self._setup_logger()  # ensure logger exists

    def get_live_trains_in_section(self):
        """Get live trains between GY and GTL using /trains/between"""
        url = f"{self.base_url}/trains/between?from={self.from_station}&to={self.to_station}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            self.logger.info("Live data fetched successfully")
            return data['data']  # List of trains
        except Exception as e:
            self.logger.error(f"Failed to fetch live data: {str(e)}")
            return []  # Fallback empty

    def get_train_live_status(self, train_number, journey_date):
        """Get live status for specific train using /trains/{trainNumber}?journeyDate=...&dataType=live"""
        url = f"{self.base_url}/trains/{train_number}?journeyDate={journey_date}&dataType=live"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()['data']
        except Exception as e:
            self.logger.error(f"Failed to fetch live status for {train_number}: {str(e)}")
            return None

    def _wait_for_rate_limit(self, endpoint):
        """Wait if needed to respect rate limits"""
        current_time = time.time()
        if endpoint in self.last_request_time:
            elapsed = current_time - self.last_request_time[endpoint]
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed
                self.logger.info(f"Rate limit: waiting {wait_time:.1f}s for {endpoint}")
                time.sleep(wait_time)

    def _make_request(self, endpoint, params=None):
        """Make rate-limited API request with caching"""
        cache_key = f"{endpoint}_{str(params) if params else ''}"

        # Check cache first
        use_cache, cached_data = self._should_use_cache(cache_key)
        if use_cache:
            self.logger.info(f"Using cached data for {endpoint}")
            return cached_data

        # Wait for rate limit
        self._wait_for_rate_limit(endpoint)

        # Make request
        url = f"{self.base_url}/{endpoint}"
        try:
            self.logger.info(f"Making API request to {endpoint}")
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 429:
                self.logger.warning("Rate limited (429), using cache if available")
                if cache_key in self.cache:
                    return self.cache[cache_key][0]
                else:
                    return {"error": "Rate limited and no cache available"}

            response.raise_for_status()
            data = response.json()

            # Cache successful response
            self.cache[cache_key] = (data, time.time())
            self.last_request_time[endpoint] = time.time()

            return data

        except HTTPError as e:
            self.logger.error(f"HTTP error for {endpoint}: {e}")
            if cache_key in self.cache:
                self.logger.info("Falling back to cached data")
                return self.cache[cache_key][0]
            return {"error": f"HTTP error: {e}"}

        except RequestException as e:
            self.logger.error(f"Request error for {endpoint}: {e}")
            if cache_key in self.cache:
                return self.cache[cache_key][0]
            return {"error": f"Request error: {e}"}
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
                return cached_data  # already in "list of trains" form

        # Wait to respect min_request_interval
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            time.sleep(wait_time)

        url = f"{self.base_url}/trains/between"
        try:
            resp = self.session.get(url, params={"from": from_station, "to": to_station}, timeout=20)
            resp.raise_for_status()
            payload = resp.json()

            if not payload.get("success", True):
                self.logger.warning("RailRadar trains/between success=false: %s", payload)

            trains_list = payload.get("data", [])  # ensure we return the array
            # Cache results
            self.cache[cache_key] = (trains_list, time.time())
            self.last_request_time = time.time()
            return trains_list

        except HTTPError as e:
            self.logger.exception("HTTP error on trains/between: %s", e)
            if cache_key in self.cache:
                self.logger.info("Using cached trains due to HTTP error")
                return self.cache[cache_key][0]
            else:
                raise
        except Exception as e:
            self.logger.exception("Error on trains/between: %s", e)
            if cache_key in self.cache:
                self.logger.info("Using cached trains due to error")
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
            response = self.session.get(url, params=params, timeout=20)  # use session
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
            response = self.session.get(url, params=params, timeout=20)  # use session
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
            response = self.session.get(url, timeout=20)  # use session
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

    def detect_abnormalities(self, static_schedules):
        """Compare live with static, detect delays/stops"""
        live_trains = self.get_live_trains_in_section()
        abnormalities = []
        for train in live_trains:
            train_num = train['trainNumber']
            if train_num in static_schedules:
                static = static_schedules[train_num]
                live_status = self.get_train_live_status(train_num, Config.get_date())
                if live_status:
                    delay = live_status.get('overallDelayMinutes', 0)
                    if delay > Config.DELAY_THRESHOLD_MINUTES:
                        abnormalities.append({
                            'train_number': train_num,
                            'type': 'delay',
                            'delay_min': delay,
                            'detected_at': Config.get_timestamp()  # Fix: Add 'detected_at'
                        })
                    # Check stoppage (simplified)
                    if live_status['currentLocation'].get('status') == 'STOPPED' and live_status.get('distanceFromLastStationKm', 0) == 0:
                        stop_time = (datetime.now() - datetime.fromisoformat(live_status['lastUpdatedAt'])).total_seconds() / 60
                        if stop_time > Config.STOPPAGE_THRESHOLD_MINUTES:
                            abnormalities.append({
                                'train_number': train_num,
                                'type': 'stoppage',
                                'stop_min': stop_time,
                                'detected_at': Config.get_timestamp()
                            })
        return abnormalities

    def _calculate_data_quality(self, static_count, live_count):
        """Calculate data quality metrics"""
        if static_count == 0:
            return {"coverage": 0, "freshness": 0, "completeness": 0}

        coverage = min(100, (live_count / static_count) * 100)
        freshness = 85  # Assume good freshness if we got data
        completeness = coverage  # Simple approximation

        return {
            "coverage": round(coverage, 1),
            "freshness": round(freshness, 1),
            "completeness": round(completeness, 1)
        }

    def _time_to_minutes(self, time_str):
        """Convert time string to minutes since midnight"""
        try:
            hour, minute = map(int, time_str.split(":"))
            return hour * 60 + minute
        except:
            return 360  # Default 6:00 AM

    def collect_section_data(self, from_station: str, to_station: str) -> Dict:
        """Comprehensive data collection for a railway section"""
        self.logger.info(f"Collecting data for section {from_station}-{to_station}")

        # Get trains running in this section
        section_trains = self.fetch_section_trains(from_station, to_station)  # now a list

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
            # RailRadar trains/between uses keys like trainNumber (camel), ensure compatibility
            train_number = train.get("trainNumber") or train.get("train_number")  # robust key
            if not train_number:
                continue

            # Get static schedule focused on section
            journey_date = self.get_running_journey_date(train_number) or datetime.now().strftime("%Y-%m-%d")
            schedule_data = self.fetch_train_schedule(train_number, journey_date)

            if schedule_data and schedule_data.get("route"):
                route = schedule_data["route"]
                entry_stop = next((s for s in route if s.get("station", {}).get("code") == from_station), None)
                exit_stop = next((s for s in route if s.get("station", {}).get("code") == to_station), None)

                if entry_stop and exit_stop:
                    static_schedules[train_number] = {
                        "train_name": (schedule_data.get("train") or {}).get("name", ""),
                        "entry_time": self._parse_time_to_minutes((entry_stop.get("schedule") or {}).get("departure")),
                        "exit_time": self._parse_time_to_minutes((exit_stop.get("schedule") or {}).get("arrival")),
                        "distance": (exit_stop.get("distanceKilometers", 0) or 0) - (
                                    entry_stop.get("distanceKilometers", 0) or 0),
                        "entry_platform": (entry_stop.get("schedule") or {}).get("platform"),
                        "exit_platform": (exit_stop.get("schedule") or {}).get("platform"),
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
                "schedule_coverage": (len(static_schedules) / len(section_trains)) if section_trains else 0,
                "live_data_coverage": (len(live_data) / len(static_schedules)) if static_schedules else 0
            }
        }

        self.logger.info(
            f"Section data collected: {len(static_schedules)} schedules, {len(live_data)} live, {len(abnormalities)} abnormalities")
        return result

    def _load_static_schedules(self):
        """Load static schedules from data.jio"""
        try:
            with open("data.jio", "r") as f:
                schedules = json.load(f)

            processed = {}
            for schedule in schedules:
                train_id = schedule.get("train_id")
                if train_id:
                    processed[train_id] = {
                        "train_name": schedule.get("train_name", "Unknown"),
                        "entry_time": self._time_to_minutes(schedule.get("scheduled_departure", "06:00")),
                        "exit_time": self._time_to_minutes(schedule.get("scheduled_arrival", "07:00")),
                        "entry_platform": schedule.get("platform", "1"),
                        "journey_date": schedule.get("journey_date", datetime.now().strftime("%Y-%m-%d"))
                    }

            return processed

        except FileNotFoundError:
            self.logger.error("data.jio file not found")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading static schedules: {e}")
            return {}

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

    def __init__(self, api_key):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})
        self.base_url = "https://railradar.in/api/v1"
        self.headers = {"x-api-key": api_key}
        self.cache = {}
        self.last_request_time = {}
        self.min_request_interval = 120  # 2 minutes in seconds
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger('DataCollector')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[DATA] %(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _should_use_cache(self, cache_key: str) -> tuple:
        """Check if cached data should be used"""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.min_request_interval:
                return True, cached_data
        return False, None

    def _wait_for_rate_limit(self, endpoint):
        """Wait if needed to respect rate limits"""
        current_time = time.time()
        if endpoint in self.last_request_time:
            elapsed = current_time - self.last_request_time[endpoint]
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed
                self.logger.info(f"Rate limit: waiting {wait_time:.1f}s for {endpoint}")
                time.sleep(wait_time)

    def _make_request(self, endpoint, params=None):
        """Make rate-limited API request with caching"""
        cache_key = f"{endpoint}_{str(params) if params else ''}"

        # Check cache first
        use_cache, cached_data = self._should_use_cache(cache_key)
        if use_cache:
            self.logger.info(f"Using cached data for {endpoint}")
            return cached_data

        # Wait for rate limit
        self._wait_for_rate_limit(endpoint)

        # Make request
        url = f"{self.base_url}/{endpoint}"
        try:
            self.logger.info(f"Making API request to {endpoint}")
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 429:
                self.logger.warning("Rate limited (429), using cache if available")
                if cache_key in self.cache:
                    return self.cache[cache_key]
                else:
                    return {"error": "Rate limited and no cache available"}

            response.raise_for_status()
            data = response.json()

            # Cache successful response
            self.cache[cache_key] = (data, time.time())
            self.last_request_time[endpoint] = time.time()

            return data

        except HTTPError as e:
            self.logger.error(f"HTTP error for {endpoint}: {e}")
            if cache_key in self.cache:
                self.logger.info("Falling back to cached data")
                return self.cache[cache_key]
            return {"error": f"HTTP error: {e}"}

        except RequestException as e:
            self.logger.error(f"Request error for {endpoint}: {e}")
            if cache_key in self.cache:
                return self.cache[cache_key]
            return {"error": f"Request error: {e}"}

    def fetch_section_trains(self, from_station: str, to_station: str) -> List[Dict]:
        """Get trains running between stations with proper error handling"""
        try:
            self.logger.info(f"Fetching trains for section {from_station}-{to_station}")

            data = self._make_request("trains/between", {
                "from": from_station,
                "to": to_station
            })

            if isinstance(data, dict) and "error" in data:
                self.logger.warning(f"API error: {data['error']}")
                return []

            if not data.get("success", True):
                self.logger.warning(f"RailRadar API returned success=false: {data}")
                return []

            trains_list = data.get("data", [])
            self.logger.info(f"Found {len(trains_list)} trains for section")
            return trains_list

        except Exception as e:
            self.logger.error(f"Error fetching section trains: {e}")
            return []

    def fetch_train_live_status(self, train_number: str, journey_date: str = None) -> Dict:
        """Get real-time live status of a train"""
        if not journey_date:
            journey_date = datetime.now().strftime("%Y-%m-%d")

        try:
            data = self._make_request(f"trains/{train_number}", {
                "dataType": "live",
                "journeyDate": journey_date
            })

            if isinstance(data, dict) and "error" in data:
                return {}

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

        try:
            data = self._make_request(f"trains/{train_number}/schedule", {
                "journeyDate": journey_date
            })

            if isinstance(data, dict) and "error" in data:
                return {}

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
        try:
            data = self._make_request(f"trains/{train_number}/instances")

            if isinstance(data, dict) and "error" in data:
                return []

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

    def _parse_time_to_minutes(self, time_str: str) -> int:
        """Parse time string to minutes since midnight"""
        if not time_str:
            return 360  # Default 6:00 AM

        try:
            # Handle different time formats
            if ':' in time_str:
                hour, minute = map(int, time_str.split(':'))
                return hour * 60 + minute
            else:
                # If it's just a number, assume it's already in minutes
                return int(time_str)
        except:
            return 360  # Default 6:00 AM

    def detect_abnormalities(self, static_schedules: Dict, section: str) -> List[Dict]:
        """FIXED: Detect abnormalities with proper error handling"""
        abnormalities = []

        try:
            current_time = datetime.now()

            for train_id, schedule in static_schedules.items():
                journey_date = schedule.get('journey_date', current_time.strftime("%Y-%m-%d"))

                # Get live data for this train
                live_data = self.fetch_train_live_status(train_id, journey_date)

                if not live_data:
                    continue

                # Check for delay abnormality
                delay_minutes = live_data.get('overallDelayMinutes', 0)

                if delay_minutes > 10:  # DELAY_THRESHOLD_MINUTES
                    abnormality = {
                        'train_id': train_id,
                        'train_number': train_id,
                        'type': 'delay',
                        'severity': 'high' if delay_minutes > 30 else 'medium',
                        'delay_minutes': delay_minutes,
                        'current_status': live_data.get('currentLocation', {}).get('status', 'Unknown'),
                        'detected_at': current_time.isoformat(),
                        'location': section,
                        'location_name': f"{section} section",
                        'abnormality_type': 'delay',
                        'description': f"Train {train_id} delayed by {delay_minutes} minutes"
                    }
                    abnormalities.append(abnormality)

                # Check for stoppage abnormality
                current_location = live_data.get('currentLocation', {})
                if current_location.get('status') == 'STOPPED':
                    last_updated = live_data.get('lastUpdatedAt')
                    if last_updated:
                        try:
                            last_update_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            stopped_duration = (current_time - last_update_time).total_seconds() / 60

                            if stopped_duration > 5:  # STOPPAGE_THRESHOLD_MINUTES
                                abnormality = {
                                    'train_id': train_id,
                                    'train_number': train_id,
                                    'type': 'stoppage',
                                    'severity': 'high',
                                    'delay_minutes': delay_minutes,
                                    'stop_duration_minutes': stopped_duration,
                                    'current_status': 'STOPPED',
                                    'detected_at': current_time.isoformat(),
                                    'location': section,
                                    'location_name': f"{section} section",
                                    'abnormality_type': 'stoppage',
                                    'description': f"Train {train_id} stopped for {stopped_duration:.0f} minutes"
                                }
                                abnormalities.append(abnormality)
                        except:
                            pass  # Skip if time parsing fails

            self.logger.info(f"Detected {len(abnormalities)} abnormalities")
            return abnormalities

        except Exception as e:
            self.logger.error(f"Error detecting abnormalities: {e}")
            return []

    def collect_section_data(self, from_station: str, to_station: str) -> Dict:
        """FIXED: Comprehensive data collection with robust error handling"""
        self.logger.info(f"Collecting data for section {from_station}-{to_station}")

        try:
            # Get trains running in this section
            section_trains = self.fetch_section_trains(from_station, to_station)

            if not section_trains:
                # Try to load from static file as fallback
                static_schedules = self._load_static_schedules()
                if static_schedules:
                    self.logger.info("Using static schedule data as fallback")
                    return {
                        "section": f"{from_station}-{to_station}",
                        "timestamp": datetime.now().isoformat(),
                        "total_trains": len(static_schedules),
                        "valid_schedules": len(static_schedules),
                        "static_schedules": static_schedules,
                        "live_data": {},
                        "abnormalities": [],
                        "data_source": "static_fallback",
                        "message": "Using static schedule data - live API unavailable"
                    }
                else:
                    return self._create_demo_data(from_station, to_station)

            static_schedules = {}
            live_data = {}

            # Process each train
            for train in section_trains[:10]:  # Limit to 10 trains to avoid rate limits
                train_number = train.get("trainNumber") or train.get("train_number")
                if not train_number:
                    continue

                # Get static schedule focused on section
                journey_date = self.get_running_journey_date(train_number) or datetime.now().strftime("%Y-%m-%d")
                schedule_data = self.fetch_train_schedule(train_number, journey_date)

                if schedule_data and schedule_data.get("route"):
                    route = schedule_data["route"]
                    entry_stop = next((s for s in route if s.get("station", {}).get("code") == from_station), None)
                    exit_stop = next((s for s in route if s.get("station", {}).get("code") == to_station), None)

                    if entry_stop and exit_stop:
                        static_schedules[train_number] = {
                            "train_name": (schedule_data.get("train") or {}).get("name", "Unknown"),
                            "entry_time": self._parse_time_to_minutes(
                                (entry_stop.get("schedule") or {}).get("departure")),
                            "exit_time": self._parse_time_to_minutes((exit_stop.get("schedule") or {}).get("arrival")),
                            "distance": (exit_stop.get("distanceKilometers", 0) or 0) - (
                                        entry_stop.get("distanceKilometers", 0) or 0),
                            "entry_platform": (entry_stop.get("schedule") or {}).get("platform"),
                            "exit_platform": (exit_stop.get("schedule") or {}).get("platform"),
                            "journey_date": journey_date
                        }

                        # Get live data
                        live_status = self.fetch_train_live_status(train_number, journey_date)
                        if live_status:
                            live_data[train_number] = live_status

                # Rate limiting
                time.sleep(0.1)

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
                    "schedule_coverage": (len(static_schedules) / len(section_trains)) if section_trains else 0,
                    "live_data_coverage": (len(live_data) / len(static_schedules)) if static_schedules else 0
                },
                "live_entry_count": len([ld for ld in live_data.values() if ld.get('currentLocation')]),
                "live_exit_count": 0,  # Would be calculated based on destination proximity
                "data_source": "railradar_api"
            }

            self.logger.info(
                f"Section data collected: {len(static_schedules)} schedules, {len(live_data)} live, {len(abnormalities)} abnormalities")
            return result

        except Exception as e:
            self.logger.error(f"Error collecting section data: {e}")
            return self._create_demo_data(from_station, to_station)

    def _load_static_schedules(self) -> Dict:
        """Load static schedules from data.jio"""
        try:
            with open("data.jio", "r") as f:
                data = json.load(f)

            processed = {}

            # Handle different data.jio formats
            if isinstance(data, list):
                schedules = data
            elif isinstance(data, dict):
                schedules = data.get("trains", [])
            else:
                return {}

            for schedule in schedules:
                train_id = schedule.get("train_id") or schedule.get("number")
                if train_id:
                    processed[train_id] = {
                        "train_name": schedule.get("train_name") or schedule.get("name", "Unknown"),
                        "entry_time": self._parse_time_to_minutes(schedule.get("scheduled_departure", "06:00")),
                        "exit_time": self._parse_time_to_minutes(schedule.get("scheduled_arrival", "07:00")),
                        "entry_platform": schedule.get("platform", "1"),
                        "journey_date": schedule.get("journey_date", datetime.now().strftime("%Y-%m-%d"))
                    }

            self.logger.info(f"Loaded {len(processed)} static schedules")
            return processed

        except FileNotFoundError:
            self.logger.error("data.jio file not found")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading static schedules: {e}")
            return {}

    def _create_demo_data(self, from_station: str, to_station: str) -> Dict:
        """Create demo data when no real data is available"""
        demo_schedules = {
            "12345": {
                "train_name": "Demo Express",
                "entry_time": 360,  # 6:00 AM
                "exit_time": 420,  # 7:00 AM
                "entry_platform": "1",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            },
            "12346": {
                "train_name": "Test Passenger",
                "entry_time": 480,  # 8:00 AM
                "exit_time": 540,  # 9:00 AM
                "entry_platform": "2",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            },
            "12347": {
                "train_name": "Sample Local",
                "entry_time": 600,  # 10:00 AM
                "exit_time": 660,  # 11:00 AM
                "entry_platform": "1",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            }
        }

        demo_abnormalities = [
            {
                'train_id': "12345",
                'train_number': "12345",
                'type': 'delay',
                'severity': 'medium',
                'delay_minutes': 15,
                'current_status': 'Running Late',
                'detected_at': datetime.now().isoformat(),
                'location': f"{from_station}-{to_station}",
                'location_name': f"{from_station} to {to_station} section",
                'abnormality_type': 'delay',
                'description': f"Train 12345 delayed by 15 minutes"
            }
        ]

        return {
            "section": f"{from_station}-{to_station}",
            "timestamp": datetime.now().isoformat(),
            "total_trains": len(demo_schedules),
            "valid_schedules": len(demo_schedules),
            "static_schedules": demo_schedules,
            "live_data": {},
            "abnormalities": demo_abnormalities,
            "data_source": "demo",
            "live_entry_count": 1,
            "live_exit_count": 0,
            "message": "Demo data - API unavailable"
        }