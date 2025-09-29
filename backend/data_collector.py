import os
import json
import logging
import time
import requests
from datetime import datetime, timedelta
from requests.exceptions import HTTPError, RequestException
from typing import Dict, List, Optional


class RailRadarDataCollector:
    def __init__(self, api_key, config=None):
        self.api_key = api_key
        self.config = config  # Store config reference
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key})
        self.base_url = "https://railradar.in/api/v1"
        self.headers = {"x-api-key": api_key}
        self.cache = {}
        self.last_request_time = {}
        # Allow overriding rate limit window for development
        self.min_request_interval = int(os.environ.get('RAILRADAR_MIN_REQUEST_INTERVAL', '15'))  # seconds - faster for live data
        self.logger = self._setup_logger()
        
        self.logger.info(f" [DATA COLLECTOR] initialized with API key: {api_key[:20]}...")
        self.logger.info(f" [DATA COLLECTOR] Rate limit interval: {self.min_request_interval}s")
        self.logger.info(f" [DATA COLLECTOR] Config provided: {config is not None}")
        
        # Test API connectivity immediately
        self.test_api_connectivity()
        
    def test_api_connectivity(self):
        """Test if the RailRadar API is accessible with our key"""
        try:
            self.logger.info("🔍 [API TEST] Testing RailRadar API connectivity...")
            
            # Test with a simple endpoint first
            test_data = self._make_request("stations/NDLS/info")
            
            if isinstance(test_data, dict):
                if "success" in test_data and test_data["success"]:
                    self.logger.info("✅ [API TEST] RailRadar API is accessible and working!")
                    return True
                elif "error" in test_data:
                    self.logger.error(f"❌ [API TEST] API returned error: {test_data['error']}")
                    return False
            
            self.logger.warning("⚠️ [API TEST] API response format unexpected")
            return False
            
        except Exception as e:
            self.logger.error(f"💥 [API TEST] Failed to test API connectivity: {e}")
            return False
        
    def _setup_logger(self):
        logger = logging.getLogger('DataCollector')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[DATA] %(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    # --- Normalization helpers ---
    def _extract_trains_array(self, payload) -> List[Dict]:
        """Given any response shape from RailRadar 'trains/between', return a list of train dicts.
        Accepts shapes like {trains:[...]}, {data:{trains:[...]}}, {data:[...]}, or already a list.
        Any non-dict items are filtered out.
        """
        trains: List[Dict] = []
        try:
            if isinstance(payload, list):
                trains = [t for t in payload if isinstance(t, dict)]
            elif isinstance(payload, dict):
                if isinstance(payload.get('trains'), list):
                    trains = [t for t in payload['trains'] if isinstance(t, dict)]
                elif isinstance(payload.get('data'), dict) and isinstance(payload['data'].get('trains'), list):
                    trains = [t for t in payload['data']['trains'] if isinstance(t, dict)]
                elif isinstance(payload.get('data'), list):
                    trains = [t for t in payload['data'] if isinstance(t, dict)]
        except Exception as e:
            self.logger.warning(f"Normalization failed, returning empty trains list: {e}")
            trains = []
        return trains

    def _should_use_cache(self, cache_key: str) -> tuple:
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.min_request_interval:
                return True, cached_data
        return False, None

    def _wait_for_rate_limit(self, endpoint):
        current_time = time.time()
        if endpoint in self.last_request_time:
            elapsed = current_time - self.last_request_time[endpoint]
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed
                self.logger.info(f"Rate limit: waiting {wait_time:.1f}s for {endpoint}")
                time.sleep(wait_time)

    def _make_request(self, endpoint, params=None):
        cache_key = f"{endpoint}_{str(params) if params else ''}"

        use_cache, cached_data = self._should_use_cache(cache_key)
        if use_cache:
            self.logger.info(f"Using cached data for {endpoint}")
            return cached_data

        self._wait_for_rate_limit(endpoint)

        url = f"{self.base_url}/{endpoint}"
        try:
            self.logger.info(f"Making API request to {endpoint}")
            self.logger.info(f"URL: {url}")
            self.logger.info(f"Headers: {self.session.headers}")
            self.logger.info(f"Params: {params}")
            
            response = self.session.get(url, params=params, timeout=30)
            
            self.logger.info(f"Response status: {response.status_code}")
            self.logger.info(f"Response headers: {dict(response.headers)}")

            if response.status_code == 429:
                self.logger.warning("Rate limited (429), using cache if available")
                if cache_key in self.cache:
                    return self.cache[cache_key][0]
                else:
                    return {"error": "Rate limited and no cache available"}

            if response.status_code == 401:
                self.logger.error("Unauthorized (401) - API key may be invalid")
                return {"error": "Unauthorized - API key may be invalid"}

            if response.status_code == 400:
                self.logger.error(f"Bad Request (400) - {response.text}")
                return {"error": f"Bad Request: {response.text}"}

            response.raise_for_status()
            data = response.json()

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

    def fetch_section_trains(self, from_station: str, to_station: str) -> List[Dict]:
        try:
            self.logger.info(f"🔍 [LIVE API] Fetching trains between {from_station} and {to_station}")
            self.logger.info(f"🔍 [LIVE API] Using RailRadar API endpoint: trains/between")

            # Use the correct RailRadar API endpoint as per docs
            data = self._make_request("trains/between", {
                "from": from_station,
                "to": to_station
            })

            self.logger.info(f"🔍 [LIVE API] Raw response received: {type(data)}")
            
            if isinstance(data, dict) and "error" in data:
                self.logger.error(f"❌ [LIVE API] API error: {data['error']}")
                return []

            # According to RailRadar docs, trains/between returns array directly in data field
            trains_list = []
            if isinstance(data, dict):
                if "success" in data and data["success"] and "data" in data:
                    # Standard RailRadar response format
                    trains_list = data["data"] if isinstance(data["data"], list) else []
                    self.logger.info(f"✅ [LIVE API] Found {len(trains_list)} trains in standard format")
                    
                    # Log the actual response structure for debugging
                    if trains_list:
                        sample_train = trains_list[0]
                        self.logger.info(f"🔍 [LIVE API] Sample train keys: {list(sample_train.keys())}")
                        self.logger.info(f"🔍 [LIVE API] Sample train data: {json.dumps(sample_train, indent=2)[:500]}...")
                else:
                    # Try to extract from different response formats
                    trains_list = self._extract_trains_array(data)
                    self.logger.info(f"✅ [LIVE API] Found {len(trains_list)} trains after normalization")
            elif isinstance(data, list):
                trains_list = data
                self.logger.info(f"✅ [LIVE API] Found {len(trains_list)} trains in direct array format")

            # Log detailed information about the trains found
            if trains_list:
                self.logger.info(f"🚂 [LIVE API] SUCCESS! Retrieved {len(trains_list)} live trains")
                for i, train in enumerate(trains_list[:3]):  # Log first 3 trains
                    train_num = train.get('trainNumber', train.get('train_number', 'Unknown'))
                    train_name = train.get('trainName', train.get('train_name', 'Unknown'))
                    self.logger.info(f"🚂 [LIVE API] Train {i+1}: {train_num} - {train_name}")
            else:
                self.logger.warning(f"⚠️ [LIVE API] No trains found between {from_station} and {to_station}")
                self.logger.warning(f"⚠️ [LIVE API] This could mean:")
                self.logger.warning(f"⚠️ [LIVE API] 1. No trains run on this route today")
                self.logger.warning(f"⚠️ [LIVE API] 2. Station codes are incorrect")
                self.logger.warning(f"⚠️ [LIVE API] 3. API response format changed")
                
            return trains_list

        except Exception as e:
            self.logger.error(f"💥 [LIVE API] Exception fetching section trains: {e}")
            return []

    def fetch_train_live_status(self, train_number: str, journey_date: str = None) -> Dict:
        if not journey_date:
            journey_date = datetime.now().strftime("%Y-%m-%d")

        try:
            data = self._make_request(f"trains/{train_number}", {
                "dataType": "live",
                "journeyDate": journey_date
            })

            if isinstance(data, dict) and "error" in data:
                return {}

            # Handle different response formats
            live_data = None
            if isinstance(data, dict):
                if "liveData" in data:
                    live_data = data["liveData"]
                elif "data" in data and "liveData" in data["data"]:
                    live_data = data["data"]["liveData"]
                elif data.get("statusSummary") or data.get("currentLocation"):
                    # Direct live data format
                    live_data = data

            if live_data:
                self.logger.info(f"✅ Live data retrieved for train {train_number}")
                return live_data
            else:
                self.logger.warning(f"No live data for train {train_number} on {journey_date}")
                return {}

        except Exception as e:
            self.logger.error(f"Error fetching live status for {train_number}: {e}")
            return {}

    def fetch_train_schedule(self, train_number: str, journey_date: str = None) -> Dict:
        if not journey_date:
            journey_date = datetime.now().strftime("%Y-%m-%d")

        try:
            data = self._make_request(f"trains/{train_number}/schedule", {
                "journeyDate": journey_date
            })

            if isinstance(data, dict) and "error" in data:
                return {}

            # Handle different response formats
            schedule_data = None
            if isinstance(data, dict):
                if "route" in data:
                    schedule_data = data
                elif "data" in data:
                    schedule_data = data["data"]
                else:
                    schedule_data = data

            if schedule_data and schedule_data.get("route"):
                self.logger.info(f"✅ Schedule retrieved for train {train_number}")
                return schedule_data
            else:
                self.logger.warning(f"No schedule data for train {train_number}")
                return {}

        except Exception as e:
            self.logger.error(f"Error fetching schedule for {train_number}: {e}")
            return {}

    def fetch_train_instances(self, train_number: str) -> List[Dict]:
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
        instances = self.fetch_train_instances(train_number)

        for instance in instances:
            if instance.get("status") == "RUNNING" and instance.get("startDate"):
                return instance["startDate"]

        for days_back in [0, 1]:
            test_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            live_data = self.fetch_train_live_status(train_number, test_date)
            if live_data:
                return test_date

        return None

    def _parse_time_to_minutes(self, time_str: str) -> int:
        if not time_str:
            return 360  # Default 6:00 AM

        try:
            if ':' in time_str:
                hour, minute = map(int, time_str.split(':'))
                return hour * 60 + minute
            else:
                return int(time_str)
        except:
            return 360  # Default 6:00 AM

    def detect_abnormalities(self, static_schedules: Dict, section: str) -> List[Dict]:
        abnormalities = []
        try:
            current_time = datetime.now()

            for train_id, schedule in static_schedules.items():
                journey_date = schedule.get('journey_date', current_time.strftime("%Y-%m-%d"))

                live_data = self.fetch_train_live_status(train_id, journey_date)

                if not live_data:
                    continue

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
                            pass

            self.logger.info(f"Detected {len(abnormalities)} abnormalities")
            return abnormalities

        except Exception as e:
            self.logger.error(f"Error detecting abnormalities: {e}")
            return []

    def collect_section_data(self, from_station: str, to_station: str) -> Dict:
        self.logger.info(f"🚂 [LIVE DATA] Starting collection for section {from_station}-{to_station}")
        
        # Check if demo is enabled (should be False for live data)
        use_demo = bool(os.environ.get('ENABLE_DEMO', '')) or bool(getattr(self.config, 'ENABLE_DEMO', False))
        self.logger.info(f"🔧 [LIVE DATA] Demo mode status: {use_demo}")
        
        if use_demo:
            self.logger.warning(f"⚠️ [LIVE DATA] Demo mode is ENABLED - this should be FALSE for live data!")
        else:
            self.logger.info(f"✅ [LIVE DATA] Demo mode is DISABLED - proceeding with LIVE data only")

        try:
            # FORCE live data collection - NO FALLBACKS
            self.logger.info("🔍 [LIVE DATA] Attempting to fetch REAL train data from RailRadar API...")
            self.logger.info(f"🔍 [LIVE DATA] API Key: {self.api_key[:20]}...")
            self.logger.info(f"🔍 [LIVE DATA] Base URL: {self.base_url}")
            
            self.logger.info("🔍 [LIVE DATA] About to call fetch_section_trains...")
            trains_list = self.fetch_section_trains(from_station, to_station)
            self.logger.info("🔍 [LIVE DATA] fetch_section_trains completed")
            
            self.logger.info(f"🔍 [LIVE DATA] Raw API response type: {type(trains_list)}")
            self.logger.info(f"🔍 [LIVE DATA] Raw API response length: {len(trains_list) if isinstance(trains_list, list) else 'Not a list'}")
            
            # Safety: always normalize again here
            self.logger.info("🔍 [LIVE DATA] Normalizing trains list...")
            trains_list = self._extract_trains_array(trains_list)
            self.logger.info(f"🔍 [LIVE DATA] After normalization: {len(trains_list) if isinstance(trains_list, list) else 'Not a list'} trains")

            if not trains_list:
                self.logger.error("❌ [LIVE DATA] NO TRAINS FOUND from RailRadar API!")
                self.logger.error("❌ [LIVE DATA] This means either:")
                self.logger.error("❌ [LIVE DATA] 1. API authentication failed")
                self.logger.error("❌ [LIVE DATA] 2. No trains on this route today")
                self.logger.error("❌ [LIVE DATA] 3. API response format changed")
                self.logger.error("❌ [LIVE DATA] 4. Rate limiting blocked the request")
                
                # LIVE DATA ONLY - NO FALLBACKS
                return {
                    "section": f"{from_station}-{to_station}",
                    "from_station": from_station,
                    "to_station": to_station,
                    "static_schedules": {},
                    "valid_schedules": 0,
                    "abnormalities": [],
                    "timestamp": datetime.now().isoformat(),
                    "data_source": "live_api_failed",
                    "error": "No live trains found from RailRadar API"
                }
            else:
                self.logger.info(f"✅ [LIVE DATA] SUCCESS! Found {len(trains_list)} trains from RailRadar API")
                
                # Log first few trains for debugging
                for i, train in enumerate(trains_list[:3]):
                    self.logger.info(f"🚂 [LIVE DATA] Sample train {i+1}: {train.get('number', 'No number')} - {train.get('name', 'No name')}")
                
                # Process the trains list into static schedules format
                static_schedules = {}
                live_data_map = {}
                for train in trains_list:
                    # Some providers may return simple strings; skip non-dicts safely
                    if not isinstance(train, dict):
                        self.logger.warning(f"Skipping non-dict train item: {str(train)[:50]}")
                        continue

                    # RailRadar trains/between model hints:
                    # number, name, source{code,name}, destination{...},
                    # journeySegment: { from{...}, to{...}, departureTime, arrivalTime }
                    train_id = train.get("number") or train.get("train_id") or train.get("train_number")
                    if not train_id:
                        # try nested structure fallback
                        tinfo = train.get("train") if isinstance(train.get("train"), dict) else {}
                        train_id = tinfo.get("number")
                    if not train_id:
                        self.logger.warning("Skipping train without 'number'")
                        continue
                    self.logger.info(f"Processing train {train_id}")

                    seg = train.get("journeySegment") or train.get("journey_segment") or {}
                    dep_str = None
                    arr_str = None
                    if isinstance(seg, dict):
                        dep_str = seg.get("departureTime") or seg.get("departure_time")
                        arr_str = seg.get("arrivalTime") or seg.get("arrival_time")
                    dep_str = dep_str or train.get("departure") or "06:00"
                    arr_str = arr_str or train.get("arrival") or "07:00"

                    tname = train.get("name") or train.get("train_name")
                    if not tname and isinstance(train.get("train"), dict):
                        tname = train["train"].get("name")

                    static_schedules[train_id] = {
                        "train_name": tname or "Unknown",
                        "entry_time": self._parse_time_to_minutes(dep_str),
                        "exit_time": self._parse_time_to_minutes(arr_str),
                        "entry_platform": train.get("platform", "TBD"),
                        "journey_date": train.get("journey_date", datetime.now().strftime("%Y-%m-%d"))
                    }

                    # Try to fetch live status for this train and store it
                    try:
                        journey_date = self.get_running_journey_date(train_id)
                        if journey_date:
                            self.logger.info(f"Fetching live status for train {train_id} on {journey_date}")
                            live = self.fetch_train_live_status(train_id, journey_date)
                            if isinstance(live, dict) and live:
                                live_data_map[train_id] = live
                                self.logger.info(f"✅ Live data stored for train {train_id}")
                            else:
                                self.logger.warning(f"No live data for train {train_id}")
                    except Exception as e:
                        self.logger.warning(f"Live fetch failed for {train_id}: {e}")
            
            # If we still don't have any schedules, check if demo is enabled
            if not static_schedules:
                self.logger.warning("No static schedules found")
                # Demo data is OFF by default, only enabled if ENABLE_DEMO=1 is set
                use_demo = bool(os.environ.get('ENABLE_DEMO', '')) or bool(getattr(self.config, 'ENABLE_DEMO', False))
                
                self.logger.info(f"🔧 Data Collection Mode: {'DEMO' if use_demo else 'LIVE'}")
                self.logger.info(f"🚉 Section: {from_station} → {to_station}")
                
                if use_demo:
                    self.logger.info("Using demo data as fallback")
                    return self._create_demo_data(from_station, to_station)
                else:
                    self.logger.info("Demo disabled; returning empty payload")
                    return {
                        "section": f"{from_station}-{to_station}",
                        "from_station": from_station,
                        "to_station": to_station,
                        "static_schedules": {},
                        "valid_schedules": 0,
                        "abnormalities": [],
                        "timestamp": datetime.now().isoformat(),
                        "data_source": "none"
                    }
                
            # Detect abnormalities in the section
            section = f"{from_station}-{to_station}"
            abnormalities = self.detect_abnormalities(static_schedules, section)
            
            # Prepare the response
            result = {
                "section": section,
                "from_station": from_station,
                "to_station": to_station,
                "static_schedules": static_schedules,
                "valid_schedules": len(static_schedules),
                "abnormalities": abnormalities,
                "timestamp": datetime.now().isoformat(),
                "data_source": "api" if trains_list else "static"
            }
            # attach live_data if present (either from API or demo)
            try:
                if 'live_data' in locals() and isinstance(live_data, dict):
                    result["live_data"] = live_data
                elif 'live_data_map' in locals() and live_data_map:
                    result["live_data"] = live_data_map
            except Exception:
                pass
            
            self.logger.info(f"Collected data for section {section} with {len(static_schedules)} trains and {len(abnormalities)} abnormalities")
            return result

        except Exception as e:
            self.logger.error(f"💥 [LIVE DATA] CRITICAL ERROR in collect_section_data: {e}")
            self.logger.error(f"💥 [LIVE DATA] Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"💥 [LIVE DATA] Full traceback: {traceback.format_exc()}")
            # Demo only if explicitly enabled
            if os.environ.get('ENABLE_DEMO', ''):
                self.logger.info("Falling back to demo data due to error (unset ENABLE_DEMO to prevent)")
                return self._create_demo_data(from_station, to_station)
            self.logger.info("Demo disabled; returning empty payload on error")
            return {
                "section": f"{from_station}-{to_station}",
                "from_station": from_station,
                "to_station": to_station,
                "static_schedules": {},
                "valid_schedules": 0,
                "abnormalities": [],
                "timestamp": datetime.now().isoformat(),
                "data_source": "error"
            }

    def _load_static_schedules(self) -> Dict:
        try:
            with open("data.jio", "r") as f:
                data = json.load(f)

            processed = {}

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
        """Create comprehensive demo data that shows the complete system flow"""
        
        # Realistic train schedules with various types
        demo_schedules = {
            "12627": {
                "train_name": "Gooty Express",
                "entry_time": 360,  # 6:00 AM
                "exit_time": 420,   # 7:00 AM
                "distance": 45,
                "entry_platform": "1",
                "exit_platform": "2",
                "journey_date": datetime.now().strftime("%Y-%m-%d"),
                "train_type": "Express",
                "priority": "high"
            },
            "56501": {
                "train_name": "Guntakal Passenger",
                "entry_time": 480,  # 8:00 AM
                "exit_time": 540,   # 9:00 AM
                "distance": 45,
                "entry_platform": "2",
                "exit_platform": "1",
                "journey_date": datetime.now().strftime("%Y-%m-%d"),
                "train_type": "Passenger",
                "priority": "medium"
            },
            "12628": {
                "train_name": "Southern Express",
                "entry_time": 600,  # 10:00 AM
                "exit_time": 660,   # 11:00 AM
                "distance": 45,
                "entry_platform": "1",
                "exit_platform": "3",
                "journey_date": datetime.now().strftime("%Y-%m-%d"),
                "train_type": "Express",
                "priority": "high"
            },
            "56502": {
                "train_name": "Local Passenger",
                "entry_time": 720,  # 12:00 PM
                "exit_time": 780,   # 1:00 PM
                "distance": 45,
                "entry_platform": "2",
                "exit_platform": "1",
                "journey_date": datetime.now().strftime("%Y-%m-%d"),
                "train_type": "Passenger",
                "priority": "medium"
            },
            "12629": {
                "train_name": "Chennai Express",
                "entry_time": 840,  # 2:00 PM
                "exit_time": 900,   # 3:00 PM
                "distance": 45,
                "entry_platform": "1",
                "exit_platform": "2",
                "journey_date": datetime.now().strftime("%Y-%m-%d"),
                "train_type": "Express",
                "priority": "high"
            }
        }

        # Realistic live data showing delays and status
        demo_live_data = {
            "12627": {
                "trainNumber": "12627",
                "trainName": "Gooty Express",
                "journeyDate": datetime.now().strftime("%Y-%m-%d"),
                "lastUpdatedAt": datetime.now().isoformat(),
                "currentLocation": {
                    "latitude": 15.2993,
                    "longitude": 77.7908,
                    "stationCode": from_station,
                    "status": "Running Late",
                    "distanceFromOriginKm": 0,
                    "distanceFromLastStationKm": 5
                },
                "overallDelayMinutes": 18,
                "dataSource": "RailRadar",
                "statusSummary": "Delayed",
                "route": []
            },
            "56501": {
                "trainNumber": "56501",
                "trainName": "Guntakal Passenger",
                "journeyDate": datetime.now().strftime("%Y-%m-%d"),
                "lastUpdatedAt": datetime.now().isoformat(),
                "currentLocation": {
                    "latitude": 15.2993,
                    "longitude": 77.7908,
                    "stationCode": from_station,
                    "status": "STOPPED",
                    "distanceFromOriginKm": 0,
                    "distanceFromLastStationKm": 0
                },
                "overallDelayMinutes": 25,
                "dataSource": "RailRadar",
                "statusSummary": "Stopped",
                "route": []
            },
            "12628": {
                "trainNumber": "12628",
                "trainName": "Southern Express",
                "journeyDate": datetime.now().strftime("%Y-%m-%d"),
                "lastUpdatedAt": datetime.now().isoformat(),
                "currentLocation": {
                    "latitude": 15.2993,
                    "longitude": 77.7908,
                    "stationCode": from_station,
                    "status": "On Time",
                    "distanceFromOriginKm": 0,
                    "distanceFromLastStationKm": 10
                },
                "overallDelayMinutes": 2,
                "dataSource": "RailRadar",
                "statusSummary": "Running",
                "route": []
            }
        }

        # Multiple abnormalities to show AI processing
        demo_abnormalities = [
            {
                'train_id': "12627",
                'train_number': "12627",
                'type': 'delay',
                'severity': 'high',
                'delay_minutes': 18,
                'current_status': 'Running Late',
                'detected_at': datetime.now().isoformat(),
                'location': from_station,
                'location_name': f"{from_station} Junction",
                'abnormality_type': 'delay',
                'description': f"Train 12627 (Gooty Express) delayed by 18 minutes due to signal failure",
                'journey_date': datetime.now().strftime("%Y-%m-%d")
            },
            {
                'train_id': "56501",
                'train_number': "56501",
                'type': 'stoppage',
                'severity': 'high',
                'delay_minutes': 25,
                'stop_duration_minutes': 8,
                'current_status': 'STOPPED',
                'detected_at': datetime.now().isoformat(),
                'location': from_station,
                'location_name': f"{from_station} Junction",
                'abnormality_type': 'stoppage',
                'description': f"Train 56501 (Guntakal Passenger) stopped for 8 minutes - technical issue",
                'journey_date': datetime.now().strftime("%Y-%m-%d")
            }
        ]

        return {
            "section": f"{from_station}-{to_station}",
            "timestamp": datetime.now().isoformat(),
            "total_trains": len(demo_schedules),
            "valid_schedules": len(demo_schedules),
            "static_schedules": demo_schedules,
            "live_data": demo_live_data,
            "abnormalities": demo_abnormalities,
            "data_source": "comprehensive_demo",
            "live_entry_count": len(demo_live_data),
            "live_exit_count": 0,
            "data_quality": {
                "schedule_coverage": 100,
                "live_data_coverage": len(demo_live_data) / len(demo_schedules) * 100
            },
            "message": "Comprehensive demo data showing complete VyuhMitra workflow"
        }

    def save_section_data(self, section_data: Dict, filepath: str = None) -> str:
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
