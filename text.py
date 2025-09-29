import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
from datetime import datetime, timedelta
import threading

# Your APIs
RAILRADAR_API_KEY = "rr_live_ccW7ci-7ty2l8DR_yceDZjpJf9PaIPKg"
GEMINI_API_KEY = "AIzaSyACfh5_Vvhmg_S2aoCH95KYIfprGG4PQiE"


class TrainControlUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Train Delay Analyzer")
        self.root.geometry("1000x700")

        # Global variables from your original code
        self.next_station_info = None
        self.station_live_data = None

        self.create_widgets()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(main_frame, text="🚆 AI-Powered Train Delay Analyzer",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)

        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(input_frame, text="Train Number:").grid(row=0, column=0, padx=5)
        self.train_entry = ttk.Entry(input_frame, width=15)
        self.train_entry.insert(0, "11055")
        self.train_entry.grid(row=0, column=1, padx=5)

        self.analyze_btn = ttk.Button(input_frame, text="Analyze Train",
                                      command=self.start_analysis)
        self.analyze_btn.grid(row=0, column=2, padx=5)

        # Progress bar
        self.progress = ttk.Progressbar(input_frame, mode='indeterminate')
        self.progress.grid(row=0, column=3, padx=5)

        # Results area
        self.results_text = scrolledtext.ScrolledText(main_frame, height=30, width=120,
                                                      font=('Consolas', 10))
        self.results_text.grid(row=2, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

    def start_analysis(self):
        """Start analysis in a separate thread to keep UI responsive"""
        train_number = self.train_entry.get().strip()
        if not train_number:
            messagebox.showerror("Error", "Please enter a train number")
            return

        self.analyze_btn.config(state='disabled')
        self.progress.start()
        self.results_text.delete(1.0, tk.END)
        self.log("🚀 Starting analysis...\n")

        # Run in separate thread
        thread = threading.Thread(target=self.analyze_train, args=(train_number,))
        thread.daemon = True
        thread.start()

    def log(self, message):
        """Add message to results text area"""
        self.results_text.insert(tk.END, message)
        self.results_text.see(tk.END)
        self.root.update()

    def analyze_train(self, train_number):
        """Your original analysis code adapted for GUI"""
        try:
            # Step 1: Fetch live data
            self.log("🔍 Fetching LIVE train data...\n")
            live_data = self.fetch_live_train_data(train_number)
            if not live_data:
                self.log("❌ No live data found for this train number.\n")
                self.log("💡 Try these sample numbers: 11055, 22649, 12009\n")
                return

            # Step 2: Fetch static data
            self.log("📅 Fetching static schedule data...\n")
            static_data = self.fetch_static_schedule_data(train_number)
            if not static_data:
                self.log("❌ No static schedule data found.\n")
                return

            self.log("✅ Both datasets fetched successfully!\n\n")

            # Step 3: AI Analysis
            self.log("🤖 Analyzing with AI...\n")
            analysis_result = self.ask_gemini_for_analysis(live_data, static_data)

            if analysis_result:
                self.log("\n" + "=" * 60 + "\n")
                self.log("🎯 TRAIN ANALYSIS RESULT:\n")
                self.log("=" * 60 + "\n")

                if isinstance(analysis_result, dict):
                    self.display_analysis_results(analysis_result)
                else:
                    self.log(f"Raw response:\n{analysis_result}\n")

                # Step 4: Check for delays
                if isinstance(analysis_result, dict):
                    self.check_delay_and_analyze(analysis_result)

        except Exception as e:
            self.log(f"💥 Error: {str(e)}\n")
        finally:
            self.progress.stop()
            self.analyze_btn.config(state='normal')

    def display_analysis_results(self, analysis_result):
        """Display analysis results in formatted way"""
        # Basic train info
        self.log(f"Train Number: {analysis_result.get('train_number', 'N/A')}\n")
        self.log(f"Train Name: {analysis_result.get('train_name', 'N/A')}\n")
        self.log(f"Current Location: {analysis_result.get('current_location', 'N/A')}\n")
        self.log(f"Status: {analysis_result.get('status_summary', 'N/A')}\n")

        delay = analysis_result.get('current_delay_minutes', 0)
        delay_status = "🟢 On Time" if delay <= 5 else "🟡 Minor Delay" if delay <= 15 else "🔴 Significant Delay"
        self.log(f"Current Delay: {delay} minutes ({delay_status})\n")

        # Next station info
        next_station = analysis_result.get('next_station', {})
        if next_station:
            self.log(f"\n📍 Next Station: {next_station.get('name', 'N/A')} ({next_station.get('code', 'N/A')})\n")
            self.log(f"   Scheduled: {next_station.get('scheduled_time', 'N/A')}\n")
            self.log(f"   Expected: {next_station.get('actual_time', 'N/A')}\n")
            self.log(f"   Delay: {next_station.get('delay_minutes', 0)} minutes\n")

    def check_delay_and_analyze(self, analysis_result):
        """Your original delay analysis code"""
        try:
            delay = analysis_result.get('current_delay_minutes', 0)
            next_station_delay = analysis_result.get('next_station', {}).get('delay_minutes', 0)

            self.log(f"\n⏰ DELAY ANALYSIS:\n")
            self.log(f"   Current Delay: {delay} minutes\n")
            self.log(f"   Next Station Delay: {next_station_delay} minutes\n")

            if delay > 0 or next_station_delay > 0:
                self.log(f"🚨 DELAY DETECTED! Starting comprehensive analysis...\n")

                next_station_info = analysis_result.get('next_station', {})
                if next_station_info and next_station_info.get('code') not in ['N/A', 'Unknown', '']:
                    station_code = next_station_info.get('code', 'Unknown')

                    self.log(f"📍 Next Station: {next_station_info.get('name', 'Unknown')} ({station_code})\n")

                    # Fetch station data
                    station_data = self.fetch_station_live_data(station_code)
                    if station_data:
                        # Analyze delay reason
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        delay_reason = self.ask_gemini_for_delay_reason(analysis_result, station_data, current_time)

                        if delay_reason:
                            self.log("\n" + "=" * 60 + "\n")
                            self.log("🔍 DELAY REASON ANALYSIS:\n")
                            self.log("=" * 60 + "\n")
                            self.log(json.dumps(delay_reason, indent=2, ensure_ascii=False) + "\n")

                            # Find solution
                            solution = self.ask_gemini_for_solution(analysis_result, station_data, delay_reason,
                                                                    current_time)

                            if solution:
                                self.log("\n" + "=" * 60 + "\n")
                                self.log("🚀 OPTIMAL SOLUTION:\n")
                                self.log("=" * 60 + "\n")
                                self.log(json.dumps(solution, indent=2, ensure_ascii=False) + "\n")

                                # Actionable summary
                                self.log("\n" + "=" * 60 + "\n")
                                self.log("📋 ACTIONABLE SUMMARY:\n")
                                self.log("=" * 60 + "\n")

                                if solution.get('free_platform_found'):
                                    self.log(f"✅ FREE PLATFORM FOUND: Platform {solution.get('suggested_platform')}\n")
                                    self.log("🔄 SUGGESTED ACTIONS:\n")
                                    for action in solution.get('suggested_actions', []):
                                        self.log(f"   • {action}\n")
                                else:
                                    self.log("⏳ NO FREE PLATFORMS AVAILABLE\n")
                                    self.log(
                                        f"⏰ ESTIMATED WAITING TIME: {solution.get('waiting_time_minutes', 'Unknown')} minutes\n")
                                    self.log("📈 THROUGHPUT SUGGESTIONS:\n")
                                    for suggestion in solution.get('throughput_suggestions', []):
                                        self.log(f"   • {suggestion}\n")

                                self.log(
                                    f"\n🎯 IMMEDIATE ACTIONS: {solution.get('immediate_actions', 'No specific actions')}\n")
        except Exception as e:
            self.log(f"💥 Error in delay analysis: {str(e)}\n")

    # YOUR ORIGINAL API FUNCTIONS (copy-pasted from your working code)
    def fetch_live_train_data(self, train_number):
        """Fetch live train data from RailRadar API"""
        try:
            dates_to_try = [
                datetime.now().strftime("%Y-%m-%d"),
                (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            ]

            for current_date in dates_to_try:
                self.log(f"🔍 Trying date: {current_date}\n")
                response = requests.get(
                    f"https://railradar.in/api/v1/trains/{train_number}",
                    headers={"x-api-key": RAILRADAR_API_KEY},
                    params={
                        "journeyDate": current_date,
                        "dataType": "live",
                        "provider": "railradar",
                        "userId": ""
                    }
                )

                if response.status_code == 200:
                    self.log(f"✅ Live data found for date: {current_date}\n")
                    return response.json()
                else:
                    self.log(f"❌ No live data for {current_date}\n")

            return None

        except Exception as e:
            self.log(f"💥 Error fetching live data: {str(e)}\n")
            return None

    def fetch_static_schedule_data(self, train_number):
        """Fetch static schedule data from RailRadar API"""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            self.log("📅 Fetching static schedule data...\n")

            response = requests.get(
                f"https://railradar.in/api/v1/trains/{train_number}",
                headers={"x-api-key": RAILRADAR_API_KEY},
                params={
                    "journeyDate": current_date,
                    "dataType": "static",
                    "provider": "railradar",
                    "userId": ""
                }
            )

            if response.status_code == 200:
                self.log("✅ Static schedule data found!\n")
                return response.json()
            else:
                self.log(f"❌ No static data: {response.status_code}\n")
                return None

        except Exception as e:
            self.log(f"💥 Error fetching static data: {str(e)}\n")
            return None

    def fetch_station_live_data(self, station_code):
        """Fetch live station data for the next station"""
        try:
            self.log(f"📍 Fetching live data for station: {station_code}\n")

            url = f"https://railradar.in/api/v1/stations/{station_code}/live"
            params = {"hours": "2", "toStationCode": "", "type": "departures"}
            headers = {"x-api-key": RAILRADAR_API_KEY}

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                self.log(f"✅ Live station data found for {station_code}\n")
                self.station_live_data = data
                return data
            else:
                self.log(f"❌ Station API Error: {response.status_code}\n")
                return None

        except Exception as e:
            self.log(f"💥 Error fetching station data: {str(e)}\n")
            return None

    def clean_gemini_response(self, response_text):
        """Clean and extract JSON from Gemini response"""
        try:
            cleaned_text = response_text.replace('```json', '').replace('```', '').strip()
            parsed = json.loads(cleaned_text)
            return parsed
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())
                    return parsed
                except:
                    pass
            return None

    def ask_gemini_for_analysis(self, live_data, static_data):
        """Send both live and static data to Gemini for analysis"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}"

            prompt = f"""
            Analyze this train data and calculate delays by comparing STATIC schedule with LIVE running status.

            STATIC SCHEDULE DATA (Reference for scheduled times):
            {json.dumps(static_data, indent=2)}

            LIVE RUNNING DATA (Current actual status):
            {json.dumps(live_data, indent=2)}

            Return ONLY valid JSON in this format:
            {{
              "train_number": "",
              "train_name": "",  
              "current_location": "",
              "status_summary": "",
              "last_updated": "",
              "current_delay_minutes": 0,
              "next_station": {{
                "name": "",
                "code": "", 
                "scheduled_time": "",
                "actual_time": "",
                "delay_minutes": 0
              }},
              "upcoming_stations": []
            }}
            """

            payload = {"contents": [{"parts": [{"text": prompt}]}]}

            response = requests.post(url, json=payload)

            if response.status_code == 200:
                result = response.json()
                gemini_response = result['candidates'][0]['content']['parts'][0]['text']
                parsed_response = self.clean_gemini_response(gemini_response)

                if parsed_response:
                    self.next_station_info = parsed_response.get('next_station', {})
                    return parsed_response
                else:
                    self.log("⚠️ Could not parse AI response as JSON\n")
                    return gemini_response
            else:
                self.log(f"❌ AI Analysis Error: {response.status_code}\n")
                return None

        except Exception as e:
            self.log(f"💥 AI API Error: {str(e)}\n")
            return None

    def ask_gemini_for_delay_reason(self, train_info, station_data, current_time):
        """Ask Gemini to analyze delay reason based on station platform occupancy"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}"

            prompt = f"""
            CURRENT TIME: {current_time}

            ANALYZE DELAY REASON FOR TRAIN:
            {json.dumps(train_info, indent=2)}

            NEXT STATION LIVE DATA (Platform occupancy information):
            {json.dumps(station_data, indent=2)}

            TASK: 
            1. Check if the next station's platform where this train is supposed to arrive is currently occupied by another train
            2. If platform is occupied, identify which train is occupying it and for how long
            3. If platform is not occupied, check signal-related issues or other operational reasons

            Return ONLY valid JSON in this format:
            {{
              "delay_reason": "platform_occupancy/signal_issue/operational_issue",
              "platform_occupied": true/false,
              "occupying_train": "train_number if platform occupied",
              "occupation_duration": "duration in minutes if known",
              "reason_details": "detailed explanation"
            }}
            """

            payload = {"contents": [{"parts": [{"text": prompt}]}]}

            response = requests.post(url, json=payload)

            if response.status_code == 200:
                result = response.json()
                gemini_response = result['candidates'][0]['content']['parts'][0]['text']
                return self.clean_gemini_response(gemini_response)
            else:
                self.log(f"❌ AI Error: {response.status_code}\n")
                return None

        except Exception as e:
            self.log(f"💥 AI API Error: {str(e)}\n")
            return None

    def ask_gemini_for_solution(self, train_info, station_data, delay_reason, current_time):
        """Ask Gemini to provide solution based on platform availability"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}"

            prompt = f"""
            CURRENT TIME: {current_time}

            TRAIN INFORMATION:
            {json.dumps(train_info, indent=2)}

            STATION LIVE DATA (All platforms and trains):
            {json.dumps(station_data, indent=2)}

            DELAY REASON ANALYSIS:
            {json.dumps(delay_reason, indent=2)}

            URGENT TASK: Check which platforms at the next station are FREE for the next 10-15 minutes.

            DECISION MAKING:
            1. If you find a free platform that can accommodate this train:
               - Suggest rearranging the train to that free platform
               - Check if any immediate train can be passed first
               - Provide specific platform number and timing

            2. If no free platforms available:
               - Calculate minimum waiting time
               - Suggest operational adjustments
               - Provide throughput improvement suggestions

            Return ONLY valid JSON in this format:
            {{
              "solution_type": "platform_rearrangement/waiting_required",
              "free_platform_found": true/false,
              "suggested_platform": "platform_number",
              "suggested_actions": [
                "action 1",
                "action 2"
              ],
              "waiting_time_minutes": 0,
              "throughput_suggestions": [
                "suggestion 1", 
                "suggestion 2"
              ],
              "immediate_actions": "detailed action plan"
            }}
            """

            payload = {"contents": [{"parts": [{"text": prompt}]}]}

            response = requests.post(url, json=payload)

            if response.status_code == 200:
                result = response.json()
                gemini_response = result['candidates'][0]['content']['parts'][0]['text']
                return self.clean_gemini_response(gemini_response)
            else:
                self.log(f"❌ AI Error: {response.status_code}\n")
                return None

        except Exception as e:
            self.log(f"💥 AI API Error: {str(e)}\n")
            return None


if __name__ == "__main__":
    root = tk.Tk()
    app = TrainControlUI(root)
    root.mainloop()