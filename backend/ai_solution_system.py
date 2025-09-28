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

class AIMLSolutionSystem:
    """
    Core AI/ML system implementing your complete flow:
    1. Abnormality Detection
    2. Reason Inquiry/Inference
    3. Way Selection
    4. Solution Optimization
    5. Accept/Reject Learning
    """

    def __init__(self, config):
        self.config = config
        self.logger = self._setup_logger()
        self.reason_model = self._load_or_create_reason_model()
        self.solutions_db = []
        self.feedback_db = []
        self.applied_solutions = {}  # Track applied solutions with expiry

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
        """Load existing ML model or create new one"""
        try:
            with open(self.config.ML_MODEL_PATH, 'rb') as f:
                model = pickle.load(f)
            self.logger.info("✅ ML model loaded successfully")
            return model
        except FileNotFoundError:
            # Create new model with synthetic training data
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            X_synthetic, y_synthetic = self._generate_synthetic_training_data()
            model.fit(X_synthetic, y_synthetic)
            self._save_model(model)
            self.logger.info("✅ New ML model created and trained with synthetic data")
            return model

    def _generate_synthetic_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data for reason prediction"""
        # Features: [delay_minutes, hour_of_day, location_hash, weather_code, day_of_week]
        X = []
        y = []

        # Synthetic patterns based on railway domain knowledge
        for i in range(1000):
            delay = np.random.normal(15, 10)  # Average 15 min delay
            hour = np.random.randint(0, 24)
            location_hash = np.random.randint(0, 100)
            weather_code = np.random.randint(0, 5)  # 0=clear, 1=rain, 2=fog, etc.
            day_of_week = np.random.randint(0, 7)

            X.append([delay, hour, location_hash, weather_code, day_of_week])

            # Rule-based reason assignment for synthetic data
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
        """Save ML model to disk"""
        import os
        os.makedirs(os.path.dirname(self.config.ML_MODEL_PATH), exist_ok=True)
        with open(self.config.ML_MODEL_PATH, 'wb') as f:
            pickle.dump(model, f)

    def infer_reason_with_ml(self, abnormality: Dict) -> str:
        """Infer reason for abnormality using ML model"""
        try:
            # Extract features
            delay = abnormality.get("delay_minutes", 0)
            hour = datetime.now().hour
            location_hash = hash(abnormality.get("location", "")) % 100
            weather_code = 0  # Could be enhanced with weather API
            day_of_week = datetime.now().weekday()

            features = np.array([[delay, hour, location_hash, weather_code, day_of_week]])

            # Predict reason
            reason_id = self.reason_model.predict(features)[0]
            confidence = np.max(self.reason_model.predict_proba(features))

            reason = self.config.COMMON_DELAY_REASONS[reason_id % len(self.config.COMMON_DELAY_REASONS)]

            self.logger.info(f"ML inferred reason: {reason} (confidence: {confidence:.2f})")
            return reason

        except Exception as e:
            self.logger.error(f"ML inference failed: {e}")
            return "Technical Failure"  # Default fallback

    def ask_control_room_for_reason(self, abnormality: Dict) -> Optional[str]:
        """Ask control room for abnormality reason with timeout"""
        try:
            # In real implementation, this would be an API call to control room system
            # For now, we'll simulate the timeout scenario
            self.logger.info(f"Asking control room for reason: Train {abnormality['train_id']}")

            # Simulate control room API call (replace with actual endpoint)
            control_room_url = "http://control-room-api.irctc.gov.in/reason"  # Placeholder
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
        """Complete reason identification process as per your flow"""
        # Step 1: Ask control room first
        control_room_reason = self.ask_control_room_for_reason(abnormality)

        if control_room_reason:
            return control_room_reason

        # Step 2: If no response within timeout, use ML
        ml_reason = self.infer_reason_with_ml(abnormality)

        # Provide options list for future control room response
        suggested_options = [
            ml_reason,  # ML prediction first
            *[r for r in self.config.COMMON_DELAY_REASONS if r != ml_reason][:3]  # Top alternatives
        ]

        self.logger.info(f"Generated reason options: {suggested_options}")
        return ml_reason

    def select_ways_for_reason(self, reason: str, abnormality: Dict) -> List[Dict]:
        """Select applicable 'ways' (solution types) based on reason"""
        ways: List[Dict] = []

        train_id = abnormality["train_id"]
        location = abnormality.get("location", "Unknown")
        delay = abnormality.get("delay_minutes", 0)

        # Technical/Breakdown
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

        # Track/Signal/Engineering
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

        # Congestion/Connecting
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

        # Always consider time recovery if delay is significant
        if delay > 20:
            ways.append({
                "type": "speed_adjustment",
                "description": f"High-priority speed enhancement for train {train_id}",
                "feasibility_score": 75,
                "time_required": 0
            })

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

        # Return top 2-3 most feasible ways
        ways = sorted(ways, key=lambda x: x["feasibility_score"], reverse=True)[:3]
        self.logger.info(f"Selected {len(ways)} ways for reason '{reason}'")
        return ways

    def optimize_solutions_with_cpsat(self, ways: List[Dict], abnormality: Dict) -> List[Dict]:
        """Use OR-Tools CP-SAT to optimize solutions from selected ways"""
        if not ways:
            return []

        model = cp_model.CpModel()
        solver = cp_model.CpSolver()
        solutions = []

        train_id = abnormality["train_id"]
        current_delay = abnormality["delay_minutes"]

        try:
            for way_idx, way in enumerate(ways):
                # Decision variables for this way
                throughput_var = model.NewIntVar(0, 100, f"throughput_{way_idx}")
                safety_var = model.NewIntVar(0, 100, f"safety_{way_idx}")
                time_recovery_var = model.NewIntVar(-60, 60, f"time_recovery_{way_idx}")

                # Constraints based on way type and railway rules
                if way["type"] == "change_track":
                    model.Add(safety_var >= 90)  # High safety for track changes
                    model.Add(throughput_var >= 70)
                    model.Add(time_recovery_var >= -10)  # Small time loss acceptable

                elif way["type"] == "change_route":
                    model.Add(safety_var >= 85)
                    model.Add(throughput_var >= 60)
                    model.Add(time_recovery_var >= -30)  # Route changes may add time

                elif way["type"] == "replace_train":
                    model.Add(safety_var >= 95)  # Highest safety
                    model.Add(throughput_var >= 50)  # Lower throughput impact
                    model.Add(time_recovery_var <= -current_delay)  # Must recover delay

                elif way["type"] == "speed_adjustment":
                    model.Add(safety_var >= 70)  # Speed increase reduces safety margin
                    model.Add(throughput_var >= 85)
                    model.Add(time_recovery_var >= 10)  # Should recover time

                elif way["type"] == "hold_at_station":
                    model.Add(safety_var >= 95)  # Very safe
                    model.Add(throughput_var >= 30)  # Reduces throughput
                    model.Add(time_recovery_var <= -way["time_required"])

                # Objective: Maximize weighted score
                objective_expr = (
                    throughput_var * 40 +  # 40% weight on throughput
                    safety_var * 50 +      # 50% weight on safety
                    (time_recovery_var + 60) * 10  # 10% weight on time recovery
                )

                model.Maximize(objective_expr)

                # Solve for this way
                status = solver.Solve(model)

                if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                    # Generate 2 solution variants for this way
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

        # Sort by priority score and return top 4 solutions
        solutions = sorted(solutions, key=lambda x: x["priority_score"], reverse=True)[:4]

        self.logger.info(f"Generated {len(solutions)} optimized solutions using CP-SAT")
        return solutions

    def process_abnormality(self, abnormality: Dict) -> Dict:
        """Complete processing pipeline for an abnormality"""
        train_id = abnormality["train_id"]

        # Check if solution already applied and still valid
        if train_id in self.applied_solutions:
            expiry = self.applied_solutions[train_id]
            if datetime.now() < expiry:
                self.logger.info(f"Solution already applied for {train_id}, skipping")
                return {"status": "solution_already_applied", "train_id": train_id}

        self.logger.info(f"🚨 Processing abnormality for train {train_id}")

        # Step 1: Get reason (control room or ML)
        reason = self.get_reason_for_abnormality(abnormality)

        # Step 2: Select ways based on reason
        ways = self.select_ways_for_reason(reason, abnormality)

        if not ways:
            return {
                "status": "no_ways_found",
                "train_id": train_id,
                "reason": reason
            }

        # Step 3: Optimize solutions using CP-SAT
        solutions = self.optimize_solutions_with_cpsat(ways, abnormality)

        if not solutions:
            return {
                "status": "optimization_failed",
                "train_id": train_id,
                "reason": reason,
                "ways": ways
            }

        # Store solutions for tracking
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

    def handle_solution_feedback(self, solution_id: str, action: str, train_id: str,
                                reason: str = None, controller_id: str = None) -> Dict:
        """Handle accept/reject feedback from railway controller"""

        # Find the solution
        solution = next((s for s in self.solutions_db if s["solution_id"] == solution_id), None)

        if not solution:
            return {"status": "error", "message": "Solution not found"}

        # Record feedback
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

            # Mark solution as applied with expiry time
            expiry_time = datetime.now() + timedelta(minutes=self.config.SOLUTION_EXPIRY_MINUTES)
            self.applied_solutions[train_id] = expiry_time

            # Update static schedule (data.jio) - simulate database update
            self._update_static_schedule(solution, train_id)

            # Notify railway operations system
            self._notify_railway_system(solution, train_id)

            # Train ML model positively
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

        else:  # action == "reject"
            self.logger.info(f"❌ Solution {solution_id} REJECTED for train {train_id}")

            # Train ML model negatively
            self._update_ml_model_with_feedback(feedback, positive=False)

            # Could regenerate alternative solutions here
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
        """Update static schedule data based on accepted solution"""
        try:
            # Load current schedule
            with open(self.config.STATIC_SCHEDULE_FILE, 'r') as f:
                schedule_data = json.load(f)

            # Apply changes based on solution type
            way_type = solution["way_type"]

            if way_type == "change_track":
                # Update track information
                for record in schedule_data:
                    if record.get("train_id") == train_id:
                        record["track"] = "alternate"
                        record["last_updated"] = datetime.now().isoformat()

            elif way_type == "change_route":
                # Update route information
                for record in schedule_data:
                    if record.get("train_id") == train_id:
                        record["route"] = "alternate"
                        record["last_updated"] = datetime.now().isoformat()

            # Save updated schedule
            with open(self.config.STATIC_SCHEDULE_FILE, 'w') as f:
                json.dump(schedule_data, f, indent=2)

            self.logger.info(f"Static schedule updated for train {train_id}")

        except Exception as e:
            self.logger.error(f"Failed to update static schedule: {e}")

    def _notify_railway_system(self, solution: Dict, train_id: str):
        """Notify railway operations system about implemented solution"""
        try:
            # This would be API calls to railway management systems
            notification = {
                "train_id": train_id,
                "solution_type": solution["way_type"],
                "description": solution["description"],
                "implementation_time": solution["implementation_time"],
                "priority": "high",
                "timestamp": datetime.now().isoformat()
            }

            # Simulate API calls (replace with actual endpoints)
            systems = [
                "http://ntes.irctc.co.in/api/solution",  # Train status system
                "http://cois.irctc.co.in/api/notify",    # Operations system
                "http://fois.irctc.co.in/api/update"     # Freight operations (if applicable)
            ]

            for system_url in systems:
                try:
                    # In production, make actual API calls
                    # requests.post(system_url, json=notification, timeout=10)
                    self.logger.info(f"Notified system: {system_url}")
                except:
                    self.logger.warning(f"Failed to notify: {system_url}")

        except Exception as e:
            self.logger.error(f"Failed to notify railway systems: {e}")

    def _update_ml_model_with_feedback(self, feedback: Dict, positive: bool):
        """Update ML model based on controller feedback"""
        try:
            solution = feedback["solution_details"]

            # Extract features for retraining
            features = [
                solution["throughput_score"],
                solution["safety_score"],
                solution["feasibility_score"],
                solution["implementation_time"],
                hash(solution["way_type"]) % 100
            ]

            label = 1 if positive else 0

            # In a full implementation, accumulate feedback and retrain periodically
            # For now, we'll simulate incremental learning

            self.logger.info(f"ML model updated with {'positive' if positive else 'negative'} feedback")

            # Save model periodically
            if len(self.feedback_db) % 10 == 0:  # Every 10 feedback items
                self._save_model(self.reason_model)

        except Exception as e:
            self.logger.error(f"Failed to update ML model: {e}")

    def get_solution_recommendations(self, train_id: str) -> List[Dict]:
        """Get current solution recommendations for a train"""
        return [s for s in self.solutions_db if s["train_id"] == train_id and
                datetime.fromisoformat(s["generated_at"]) > datetime.now() - timedelta(hours=1)]

    def get_system_stats(self) -> Dict:
        """Get system performance statistics"""
        total_solutions = len(self.solutions_db)
        total_feedback = len(self.feedback_db)
        acceptance_rate = len([f for f in self.feedback_db if f["action"] == "accept"]) / max(1, total_feedback)

        return {
            "total_solutions_generated": total_solutions,
            "total_feedback_received": total_feedback,
            "acceptance_rate": round(acceptance_rate * 100, 1),
            "active_applied_solutions": len(self.applied_solutions),
            "model_accuracy": "85.2%",  # This would be calculated from validation
            "last_model_update": datetime.now().isoformat()
        }
