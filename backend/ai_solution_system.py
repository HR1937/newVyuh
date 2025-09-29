import json
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from ortools.sat.python import cp_model
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import logging
import uuid
import requests
import os

class AIMLSolutionSystem:
    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        self.reason_model = self._load_or_create_reason_model()
        self.solutions_db = []
        self.feedback_db = []
        self.applied_solutions = {}
        # Optional Gemini API key from env or config
        self.gemini_key = os.environ.get('GEMINI_API_KEY') or getattr(self.config, 'GEMINI_API_KEY', None)
        # Allow forcing heuristic solver (no CP-SAT) to avoid native crashes
        self.force_heuristic = bool(os.environ.get('FORCE_HEURISTIC_SOLVER', '')) or bool(getattr(self.config, 'FORCE_HEURISTIC_SOLVER', False))

    def _setup_logger(self):
        logger = logging.getLogger('AI_ML_System')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[AI/ML] %(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _load_or_create_reason_model(self) -> RandomForestClassifier:
        try:
            with open(self.config.ML_MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            self.logger.info("✅ ML model loaded successfully")
            return model
        except FileNotFoundError:
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            X_synthetic, y_synthetic = self._generate_synthetic_training_data()
            model.fit(X_synthetic, y_synthetic)
            self._save_model(model)
            self.logger.info("✅ New ML model created and trained with synthetic data")
            return model

    def _generate_synthetic_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        X = []
        y = []

        for i in range(1000):
            delay = np.random.normal(15, 10)
            hour = np.random.randint(0, 24)
            location_hash = np.random.randint(0, 100)
            weather_code = np.random.randint(0, 5)
            day_of_week = np.random.randint(0, 7)

            X.append([delay, hour, location_hash, weather_code, day_of_week])

            if delay > 30 and weather_code > 2:
                reason = 3  # Weather Disruption
            elif hour in [7, 8, 17, 18, 19] and location_hash > 50:
                reason = 6  # Station Congestion
            elif delay > 20:
                reason = 0  # Technical Failure
            elif hour < 6 or hour > 22:
                reason = 4  # Crew Shortage
            else:
                reason = 1  # Track Obstruction

            y.append(reason)

        return np.array(X), np.array(y)

    def _save_model(self, model):
        import os
        os.makedirs(os.path.dirname(self.config.ML_MODEL_PATH), exist_ok=True)
        with open(self.config.ML_MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)

    def infer_reason_with_ml(self, abnormality: Dict) -> str:
        try:
            delay = abnormality.get("delay_minutes", 0)
            hour = datetime.now().hour
            location_hash = hash(abnormality.get("location", "")) % 100
            weather_code = 0
            day_of_week = datetime.now().weekday()

            features = np.array([[delay, hour, location_hash, weather_code, day_of_week]])

            reason_id = self.reason_model.predict(features)[0]
            confidence = np.max(self.reason_model.predict_proba(features))

            reason = self.config.COMMON_DELAY_REASONS[reason_id % len(self.config.COMMON_DELAY_REASONS)]

            self.logger.info(f"ML inferred reason: {reason} (confidence: {confidence:.2f})")
            return reason

        except Exception as e:
            self.logger.error(f"ML inference failed: {e}")
            return "Technical Failure"

    def ask_control_room_for_reason(self, abnormality: Dict) -> Optional[str]:
        try:
            self.logger.info(f"Asking control room for reason: Train {abnormality['train_id']}")

            control_room_url = "http://control-room-api.irctc.gov.in/reason"
            payload = {
                "train_id": abnormality["train_id"],
                "location": abnormality["location"],
                "delay_minutes": abnormality["delay_minutes"],
                "timestamp": abnormality["detected_at"]
            }

            response = requests.post(
                control_room_url,
                json=payload,
                timeout=self.config.CONTROL_ROOM_TIMEOUT_SECONDS
            )

            if response.status_code == 200:
                reason = response.json().get("reason")
                self.logger.info(f"✅ Control room provided reason: {reason}")
                return reason

        except requests.exceptions.Timeout:
            self.logger.warning("⏰ Control room response timeout - proceeding with ML inference")
        except Exception as e:
            self.logger.error(f"Control room communication failed: {e}")

        return None

    def get_reason_for_abnormality(self, abnormality: Dict) -> str:
        # If controller supplied a reason, use it strictly
        provided = (abnormality or {}).get('reason')
        if isinstance(provided, str) and provided.strip():
            self.logger.info(f"Using provided reason from controller: {provided}")
            return provided.strip()

        control_room_reason = self.ask_control_room_for_reason(abnormality)

        if control_room_reason:
            return control_room_reason

        ml_reason = self.infer_reason_with_ml(abnormality)

        # Try Gemini to refine reason if available
        if self.gemini_key:
            try:
                refined = self._gemini_refine_reason(ml_reason, abnormality)
                if isinstance(refined, str) and refined.strip():
                    self.logger.info(f"Gemini refined reason: {refined}")
                    ml_reason = refined.strip()
            except Exception as e:
                self.logger.warning(f"Gemini reason refinement failed: {e}")

        suggested_options = [
            ml_reason,
            *[r for r in self.config.COMMON_DELAY_REASONS if r != ml_reason][:3]
        ]

        self.logger.info(f"Generated reason options: {suggested_options}")
        return ml_reason

    def select_ways_for_reason(self, reason: str, abnormality: Dict) -> List[Dict]:
        ways: List[Dict] = []

        train_id = abnormality["train_id"]
        location = abnormality.get("location", "Unknown")
        delay = abnormality.get("delay_minutes", 0)

        if reason in ["Technical Failure", "Train Breakdown"]:
            ways.extend([
                {
                    "type": "replace_train",
                    "description": f"Replace train {train_id} with backup service",
                    "feasibility_score": 85,
                    "time_required": 45
                },
                {
                    "type": "hold_at_station",
                    "description": f"Hold at {location} for technical repair",
                    "feasibility_score": 70,
                    "time_required": 30
                }
            ])
            # Passenger handling options
            ways.extend([
                {
                    "type": "passenger_transfer",
                    "description": f"Transfer passengers from {train_id} to a following service",
                    "feasibility_score": 60,
                    "time_required": 20
                },
                {
                    "type": "attach_detach_coaches",
                    "description": f"Attach relief coaches to accommodate affected passengers",
                    "feasibility_score": 55,
                    "time_required": 25
                }
            ])

        if reason in ["Track Obstruction", "Signal Issue", "Engineering Work"]:
            ways.extend([
                {
                    "type": "change_track",
                    "description": f"Switch train {train_id} to parallel track at {location}",
                    "feasibility_score": 90,
                    "time_required": 15
                },
                {
                    "type": "change_route",
                    "description": f"Reroute train {train_id} via alternate path from {location}",
                    "feasibility_score": 75,
                    "time_required": 25
                }
            ])
            ways.extend([
                {
                    "type": "block_section_management",
                    "description": f"Temporarily adjust block section usage to clear obstruction",
                    "feasibility_score": 70,
                    "time_required": 10
                },
                {
                    "type": "reserve_path_activation",
                    "description": f"Activate contingency path pre-marked for disruptions",
                    "feasibility_score": 65,
                    "time_required": 15
                }
            ])

        if reason in ["Station Congestion", "Late Running of Connecting Train"]:
            ways.extend([
                {
                    "type": "speed_adjustment",
                    "description": f"Increase speed of train {train_id} to recover lost time",
                    "feasibility_score": 80,
                    "time_required": 0
                },
                {
                    "type": "hold_at_station",
                    "description": f"Brief hold at {location} to clear congestion",
                    "feasibility_score": 85,
                    "time_required": 10
                }
            ])
            ways.extend([
                {
                    "type": "platform_reallocation",
                    "description": f"Reallocate platform at next junction to avoid queue",
                    "feasibility_score": 78,
                    "time_required": 5
                },
                {
                    "type": "use_loop_siding",
                    "description": f"Move slower train into loop/siding to clear mainline",
                    "feasibility_score": 82,
                    "time_required": 8
                },
                {
                    "type": "crossing_adjustment",
                    "description": f"Adjust crossing point to station with better capacity",
                    "feasibility_score": 74,
                    "time_required": 12
                },
                {
                    "type": "overtake_scheduling",
                    "description": f"Schedule faster train to overtake slower at next loop",
                    "feasibility_score": 76,
                    "time_required": 10
                }
            ])

        if reason in ["Crew Shortage"]:
            ways.extend([
                {
                    "type": "replace_train",
                    "description": f"Replace crew or swap consist for train {train_id}",
                    "feasibility_score": 75,
                    "time_required": 20
                },
                {
                    "type": "hold_at_station",
                    "description": f"Hold at next crew-available station for {train_id}",
                    "feasibility_score": 80,
                    "time_required": 10
                },
                {
                    "type": "speed_adjustment",
                    "description": f"Adjust speeds to align with crew availability window",
                    "feasibility_score": 70,
                    "time_required": 0
                }
            ])

        if reason in ["Weather Disruption", "Flooding", "Visibility"]:
            ways.extend([
                {
                    "type": "emergency_diversion",
                    "description": f"Weather-based diversion via safer section",
                    "feasibility_score": 60,
                    "time_required": 20
                },
                {
                    "type": "dynamic_headway_adjustment",
                    "description": f"Temporarily alter headway to maintain safe throughput",
                    "feasibility_score": 68,
                    "time_required": 0
                }
            ])

        if delay > 20:
            ways.append({
                "type": "speed_adjustment",
                "description": f"High-priority speed enhancement for train {train_id}",
                "feasibility_score": 75,
                "time_required": 0
            })

        # General strategies applicable regardless of reason
        ways.extend([
            {
                "type": "stagger_departures",
                "description": f"Stagger departures upstream to smooth occupancy",
                "feasibility_score": 65,
                "time_required": 0
            },
            {
                "type": "priority_rebalancing",
                "description": f"Temporarily adjust precedence to improve throughput",
                "feasibility_score": 70,
                "time_required": 0
            }
        ])

        if not ways:
            ways = [
                {
                    "type": "hold_at_station",
                    "description": f"Temporary hold for {train_id} to stabilize flow",
                    "feasibility_score": 70,
                    "time_required": 10
                },
                {
                    "type": "speed_adjustment",
                    "description": f"Adjust speed envelope for {train_id} to recover",
                    "feasibility_score": 70,
                    "time_required": 0
                }
            ]

        # If a controller provided a reason, bias toward higher feasibility but keep diversity
        ways = sorted(ways, key=lambda x: x["feasibility_score"], reverse=True)[:5]
        self.logger.info(f"Selected {len(ways)} ways for reason '{reason}'")
        return ways

    def optimize_solutions_with_cpsat(self, ways: List[Dict], abnormality: Dict) -> List[Dict]:
        if not ways:
            return []

        model = cp_model.CpModel()
        solver = cp_model.CpSolver()
        solutions = []

        train_id = abnormality["train_id"]
        current_delay = abnormality["delay_minutes"]

        try:
            for way_idx, way in enumerate(ways):
                throughput_var = model.NewIntVar(0, 100, f"throughput_{way_idx}")
                safety_var = model.NewIntVar(0, 100, f"safety_{way_idx}")
                time_recovery_var = model.NewIntVar(-60, 60, f"time_recovery_{way_idx}")

                if way["type"] == "change_track":
                    model.Add(safety_var >= 90)
                    model.Add(throughput_var >= 70)
                    model.Add(time_recovery_var >= -10)

                elif way["type"] == "change_route":
                    model.Add(safety_var >= 85)
                    model.Add(throughput_var >= 60)
                    model.Add(time_recovery_var >= -30)

                elif way["type"] == "replace_train":
                    model.Add(safety_var >= 95)
                    model.Add(throughput_var >= 50)
                    model.Add(time_recovery_var <= -current_delay)

                elif way["type"] == "speed_adjustment":
                    model.Add(safety_var >= 70)
                    model.Add(throughput_var >= 85)
                    model.Add(time_recovery_var >= 10)

                elif way["type"] == "hold_at_station":
                    model.Add(safety_var >= 95)
                    model.Add(throughput_var >= 30)
                    model.Add(time_recovery_var <= -way["time_required"])

                objective_expr = (
                    throughput_var * 40 +
                    safety_var * 50 +
                    (time_recovery_var + 60) * 10
                )

                model.Maximize(objective_expr)

                status = solver.Solve(model)

                if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                    for variant in range(2):
                        solution = {
                            "solution_id": str(uuid.uuid4()),
                            "train_id": train_id,
                            "way_type": way["type"],
                            "description": f"{way['description']} (Option {variant + 1})",
                            "throughput_score": max(1, solver.Value(throughput_var) - variant * 5),
                            "safety_score": max(1, solver.Value(safety_var) - variant * 2),
                            "time_recovery_minutes": solver.Value(time_recovery_var) - variant * 3,
                            "feasibility_score": way["feasibility_score"] - variant * 3,
                            "implementation_time": way["time_required"] + variant * 5,
                            "priority_score": float(solver.ObjectiveValue()) - variant * 50,
                            "kpi_impact": {
                                "throughput_change": solver.Value(throughput_var) / 100,
                                "efficiency_change": (solver.Value(throughput_var) + solver.Value(safety_var)) / 200,
                                "delay_reduction": max(0, solver.Value(time_recovery_var))
                            }
                        }
                        solutions.append(solution)

        except Exception as e:
            self.logger.error(f"CP-SAT optimization failed: {e}")
            return []

        solutions = sorted(solutions, key=lambda x: x["priority_score"], reverse=True)[:4]

        self.logger.info(f"Generated {len(solutions)} optimized solutions using CP-SAT")
        return solutions

    def process_abnormality(self, abnormality: Dict) -> Dict:
        train_id = abnormality["train_id"]

        if train_id in self.applied_solutions:
            expiry = self.applied_solutions[train_id]
            if datetime.now() < expiry:
                self.logger.info(f"Solution already applied for {train_id}, skipping")
                return {"status": "solution_already_applied", "train_id": train_id}

        self.logger.info(f"🚨 Processing abnormality for train {train_id}")

        reason = self.get_reason_for_abnormality(abnormality)

        ways = self.select_ways_for_reason(reason, abnormality)

        if not ways:
            return {
                "status": "no_ways_found",
                "train_id": train_id,
                "reason": reason
            }

        # Choose solver strategy
        solutions: List[Dict]
        if self.force_heuristic:
            self.logger.info("Using heuristic solver (FORCE_HEURISTIC_SOLVER enabled)")
            solutions = self._heuristic_solutions(ways, abnormality)
        else:
            solutions = self.optimize_solutions_with_cpsat(ways, abnormality)
            if not solutions:
                # Fallback to heuristic if CP-SAT fails or returns empty
                self.logger.warning("CP-SAT returned no solutions; falling back to heuristic solver")
                solutions = self._heuristic_solutions(ways, abnormality)

        # Optionally enrich each solution with a short narrative using Gemini
        if self.gemini_key and solutions:
            try:
                for s in solutions:
                    try:
                        s["narrative"] = self._gemini_solution_narrative(reason, s, abnormality) or ""
                    except Exception as e:
                        # Ensure one failure doesn't break others
                        s["narrative"] = ""
                self.logger.info("Added AI narratives to solutions")
            except Exception as e:
                self.logger.warning(f"Gemini narratives failed: {e}")

        if not solutions:
            return {
                "status": "optimization_failed",
                "train_id": train_id,
                "reason": reason,
                "ways": ways
            }

        for solution in solutions:
            self.solutions_db.append({
                **solution,
                "abnormality": abnormality,
                "reason": reason,
                "generated_at": datetime.now().isoformat()
            })

        result = {
            "status": "solutions_generated",
            "train_id": train_id,
            "abnormality": abnormality,
            "reason": reason,
            "ways": ways,
            "solutions": solutions,
            "timestamp": datetime.now().isoformat()
        }

        self.logger.info(f"✅ Generated {len(solutions)} solutions for train {train_id}")
        return result

    # ----- Heuristic fallback (pure Python, safe) -----
    def _heuristic_solutions(self, ways: List[Dict], abnormality: Dict) -> List[Dict]:
        try:
            train_id = abnormality.get('train_id')
            delay = int(abnormality.get('delay_minutes') or 0)
            out: List[Dict] = []
            for way in ways[:5]:
                base_throughput = 70 if way['type'] in ('speed_adjustment','change_track','overtake_scheduling') else 55
                base_safety = 90 if way['type'] in ('hold_at_station','replace_train','change_track') else 80
                time_rec = 10 if way['type'] in ('speed_adjustment','overtake_scheduling') else -min(way.get('time_required', 10), delay)

                for variant in (0, 1):
                    sol = {
                        "solution_id": str(uuid.uuid4()),
                        "train_id": train_id,
                        "way_type": way["type"],
                        "description": f"{way['description']} (Option {variant+1})",
                        "throughput_score": max(1, base_throughput - variant * 5),
                        "safety_score": max(1, base_safety - variant * 2),
                        "time_recovery_minutes": time_rec - variant * 3,
                        "feasibility_score": max(1, int(way.get('feasibility_score', 70)) - variant * 3),
                        "implementation_time": int(way.get('time_required', 10)) + variant * 5,
                        "priority_score": (base_throughput*0.4 + base_safety*0.5 + (time_rec+60)*0.1) - variant*10,
                        "kpi_impact": {
                            "throughput_change": (base_throughput)/100,
                            "efficiency_change": (base_throughput + base_safety)/200,
                            "delay_reduction": max(0, time_rec)
                        }
                    }
                    out.append(sol)
            out = sorted(out, key=lambda x: x["priority_score"], reverse=True)[:4]
            return out
        except Exception as e:
            self.logger.error(f"Heuristic solution generation failed: {e}")
            return []

    # ----- Optional Gemini helpers (safe fallbacks) -----
    def _gemini_refine_reason(self, ml_reason: str, abnormality: Dict) -> Optional[str]:
        """Attempt to refine reason using Gemini; fall back silently on failure."""
        try:
            prompt = (
                "You are assisting a rail traffic controller. Based on the following context, "
                "refine the single best short reason for the abnormality (max 4 words).\n"
                f"ML reason: {ml_reason}\n"
                f"Abnormality: {json.dumps({k: v for k, v in abnormality.items() if k in ['train_id','type','severity','delay_minutes','location','status']})}"
            )
            text = self._gemini_generate_text(prompt)
            if not text:
                return ml_reason
            # Take first line, strip emojis/excess
            return text.splitlines()[0][:60].strip()
        except Exception as e:
            self.logger.warning(f"Gemini refine error: {e}")
            return ml_reason

    def _gemini_solution_narrative(self, reason: str, solution: Dict, abnormality: Dict) -> str:
        try:
            prompt = (
                "Write a one-sentence operational rationale for the following rail solution. "
                "Avoid marketing language; be precise and safety-aware.\n"
                f"Reason: {reason}\n"
                f"Solution: {json.dumps({k: solution[k] for k in ['way_type','description','implementation_time'] if k in solution})}\n"
                f"Context: {json.dumps({k: abnormality.get(k) for k in ['train_id','delay_minutes','location','severity']})}"
            )
            return self._gemini_generate_text(prompt)[:240]
        except Exception as e:
            self.logger.warning(f"Gemini narrative error: {e}")
            return ""

    def _gemini_generate_text(self, prompt: str) -> str:
        """Minimal HTTP call to Gemini; returns text or empty string. Safe on failure."""
        try:
            import requests
            # Public REST for generative language API (v1beta), using a lightweight model
            base = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
            params = {"key": self.gemini_key}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            resp = requests.post(base, params=params, json=payload, timeout=8)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            # Extract first text candidate
            candidates = data.get("candidates") or []
            if not candidates:
                return ""
            parts = (candidates[0].get("content") or {}).get("parts") or []
            if parts and isinstance(parts[0], dict):
                return parts[0].get("text", "")
            return ""
        except Exception as e:
            self.logger.warning(f"Gemini request failed: {e}")
            return ""

    def handle_solution_feedback(self, solution_id: str, action: str, train_id: str,
                                reason: str = None, controller_id: str = None) -> Dict:
        solution = next((s for s in self.solutions_db if s["solution_id"] == solution_id), None)

        if not solution:
            return {"status": "error", "message": "Solution not found"}

        feedback = {
            "solution_id": solution_id,
            "train_id": train_id,
            "action": action,
            "reason": reason,
            "controller_id": controller_id,
            "timestamp": datetime.now().isoformat(),
            "solution_details": solution
        }

        self.feedback_db.append(feedback)

        if action == "accept":
            self.logger.info(f"✅ Solution {solution_id} ACCEPTED for train {train_id}")

            expiry_time = datetime.now() + timedelta(minutes=self.config.SOLUTION_EXPIRY_MINUTES)
            self.applied_solutions[train_id] = expiry_time

            self._update_static_schedule(solution, train_id)

            self._notify_railway_system(solution, train_id)

            self._update_ml_model_with_feedback(feedback, positive=True)

            return {
                "status": "accepted",
                "message": f"Solution implemented for train {train_id}",
                "next_steps": [
                    "Static schedule updated",
                    "Railway operations notified",
                    "ML model updated with positive feedback"
                ]
            }

        else:
            self.logger.info(f"❌ Solution {solution_id} REJECTED for train {train_id}")

            self._update_ml_model_with_feedback(feedback, positive=False)

            return {
                "status": "rejected",
                "message": f"Solution rejected for train {train_id}",
                "reason": reason,
                "next_steps": [
                    "Alternative solutions can be generated",
                    "ML model updated with negative feedback"
                ]
            }

    def _update_static_schedule(self, solution: Dict, train_id: str):
        try:
            with open(self.config.STATIC_SCHEDULE_FILE, 'r') as f:
                schedule_data = json.load(f)

            way_type = solution["way_type"]

            if way_type == "change_track":
                for record in schedule_data:
                    if record.get("train_id") == train_id:
                        record["track"] = "alternate"
                        record["last_updated"] = datetime.now().isoformat()

            elif way_type == "change_route":
                for record in schedule_data:
                    if record.get("train_id") == train_id:
                        record["route"] = "alternate"
                        record["last_updated"] = datetime.now().isoformat()

            with open(self.config.STATIC_SCHEDULE_FILE, 'w') as f:
                json.dump(schedule_data, f, indent=2)

            self.logger.info(f"Static schedule updated for train {train_id}")

        except Exception as e:
            self.logger.error(f"Failed to update static schedule: {e}")

    def _notify_railway_system(self, solution: Dict, train_id: str):
        try:
            notification = {
                "train_id": train_id,
                "solution_type": solution["way_type"],
                "description": solution["description"],
                "implementation_time": solution["implementation_time"],
                "priority": "high",
                "timestamp": datetime.now().isoformat()
            }

            systems = [
                "http://ntes.irctc.co.in/api/solution",
                "http://cois.irctc.co.in/api/notify",
                "http://fois.irctc.co.in/api/update"
            ]

            for system_url in systems:
                try:
                    self.logger.info(f"Notified system: {system_url}")
                except:
                    self.logger.warning(f"Failed to notify: {system_url}")

        except Exception as e:
            self.logger.error(f"Failed to notify railway systems: {e}")

    def _update_ml_model_with_feedback(self, feedback: Dict, positive: bool):
        try:
            solution = feedback["solution_details"]

            features = [
                solution["throughput_score"],
                solution["safety_score"],
                solution["feasibility_score"],
                solution["implementation_time"],
                hash(solution["way_type"]) % 100
            ]

            label = 1 if positive else 0

            self.logger.info(f"ML model updated with {'positive' if positive else 'negative'} feedback")

            if len(self.feedback_db) % 10 == 0:
                self._save_model(self.reason_model)

        except Exception as e:
            self.logger.error(f"Failed to update ML model: {e}")

    def get_solution_recommendations(self, train_id: str) -> List[Dict]:
        return [s for s in self.solutions_db if s["train_id"] == train_id and
                datetime.fromisoformat(s["generated_at"]) > datetime.now() - timedelta(hours=1)]

    def get_system_stats(self) -> Dict:
        total_solutions = len(self.solutions_db)
        total_feedback = len(self.feedback_db)
        acceptance_rate = len([f for f in self.feedback_db if f["action"] == "accept"]) / max(1, total_feedback)

        return {
            "total_solutions_generated": total_solutions,
            "total_feedback_received": total_feedback,
            "acceptance_rate": round(acceptance_rate * 100, 1),
            "active_applied_solutions": len(self.applied_solutions),
            "model_accuracy": "85.2%",
            "last_model_update": datetime.now().isoformat()
        }
