from ortools.sat.python import cp_model
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime
import logging

class TrainScheduleOptimizer:
    def __init__(self, min_headway_minutes: int = 5):
        self.min_headway = min_headway_minutes
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger('Optimizer')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[OPTIMIZER] %(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def optimize_section_schedule(self, static_schedules: Dict, scenario: str = 'default',
                                  extra_constraints: Dict = None) -> Dict:
        """
        Optimize train schedules using CP-SAT with scenario-based modifications
        """
        self.logger.info(f"Starting optimization for scenario: {scenario}")

        # Filter valid trains
        valid_trains = {
            train_id: data for train_id, data in static_schedules.items()
            if data.get("entry_time") is not None and data.get("exit_time") is not None
        }

        if len(valid_trains) < 2:
            return {
                "status": "insufficient_data",
                "message": "Need at least 2 trains for optimization",
                "total_trains": len(valid_trains)
            }

        # Apply scenario modifications
        modified_schedules = self._apply_scenario(valid_trains, scenario)

        # Create CP-SAT model
        model = cp_model.CpModel()
        solver = cp_model.CpSolver()

        # Decision variables - deviation from original schedule
        train_vars = {}
        deviation_vars = {}

        for train_id, schedule in modified_schedules.items():
            original_entry = schedule["entry_time"]
            original_exit = schedule["exit_time"]

            # Allow deviation of ±2 hours (120 minutes)
            max_deviation = 120

            # Entry time deviation
            entry_deviation = model.NewIntVar(-max_deviation, max_deviation, f"entry_dev_{train_id}")
            exit_deviation = model.NewIntVar(-max_deviation, max_deviation, f"exit_dev_{train_id}")

            # Actual scheduled times
            entry_time = model.NewIntVar(0, 1440, f"entry_{train_id}")  # 24 hours = 1440 minutes
            exit_time = model.NewIntVar(0, 1440, f"exit_{train_id}")

            # Link actual times to original + deviation
            model.Add(entry_time == original_entry + entry_deviation)
            model.Add(exit_time == original_exit + exit_deviation)

            # Ensure exit after entry (minimum journey time)
            journey_time = original_exit - original_entry
            model.Add(exit_time >= entry_time + max(journey_time // 2, 15))  # At least 15 min journey

            train_vars[train_id] = {
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_deviation": entry_deviation,
                "exit_deviation": exit_deviation
            }
            deviation_vars[train_id] = (entry_deviation, exit_deviation)

        # Constraint 1: Minimum headway between consecutive trains
        train_list = list(modified_schedules.keys())
        headway_constraints = 0

        for i in range(len(train_list)):
            for j in range(i + 1, len(train_list)):
                train_a = train_list[i]
                train_b = train_list[j]

                # Headway constraint: trains must be at least min_headway apart
                model.AddBoolOr([
                    train_vars[train_a]["entry_time"] + self.min_headway <= train_vars[train_b]["entry_time"],
                    train_vars[train_b]["entry_time"] + self.min_headway <= train_vars[train_a]["entry_time"]
                ])
                headway_constraints += 1

        # Constraint 2: Platform conflicts (same platform needs extra separation)
        platform_constraints = 0
        for i in range(len(train_list)):
            for j in range(i + 1, len(train_list)):
                train_a = train_list[i]
                train_b = train_list[j]

                platform_a = modified_schedules[train_a].get("entry_platform")
                platform_b = modified_schedules[train_b].get("entry_platform")

                if platform_a and platform_b and platform_a == platform_b:
                    # Same platform needs 10 minutes separation
                    model.AddBoolOr([
                        train_vars[train_a]["entry_time"] + 10 <= train_vars[train_b]["entry_time"],
                        train_vars[train_b]["entry_time"] + 10 <= train_vars[train_a]["entry_time"]
                    ])
                    platform_constraints += 1

        # Constraint 3: Scenario-specific constraints
        if scenario == 'reduce_headway':
            # Try to achieve 3-minute headway
            self.min_headway = 3
        elif scenario == 'weather_disruption':
            # Add buffer time for all trains
            for train_id in train_vars:
                model.Add(deviation_vars[train_id][0] >= 10)  # At least 10 min delay
        elif scenario == 'add_delay':
            # Add delay to first train
            first_train = train_list[0]
            model.Add(deviation_vars[first_train][0] >= 20)  # 20 min delay

        # Objective: Minimize total absolute deviations
        abs_deviations = []
        for train_id, (entry_dev, exit_dev) in deviation_vars.items():
            abs_entry = model.NewIntVar(0, 240, f"abs_entry_{train_id}")
            abs_exit = model.NewIntVar(0, 240, f"abs_exit_{train_id}")

            model.AddAbsEquality(abs_entry, entry_dev)
            model.AddAbsEquality(abs_exit, exit_dev)

            abs_deviations.extend([abs_entry, abs_exit])

        total_deviation = model.NewIntVar(0, 10000, "total_deviation")
        model.Add(total_deviation == sum(abs_deviations))

        model.Minimize(total_deviation)

        # Solve
        start_time = datetime.now()
        solver.parameters.max_time_in_seconds = 30  # 30 second timeout

        status = solver.Solve(model)
        solve_time = (datetime.now() - start_time).total_seconds()

        self.logger.info(f"Model created: {len(valid_trains)} trains, {headway_constraints} headway constraints, {platform_constraints} platform constraints")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            # Extract solution
            optimized_schedule = {}
            total_deviation_value = solver.Value(total_deviation)
            trains_adjusted = 0

            for train_id in train_vars:
                entry_dev = solver.Value(deviation_vars[train_id][0])
                exit_dev = solver.Value(deviation_vars[train_id][1])

                optimized_entry = solver.Value(train_vars[train_id]["entry_time"])
                optimized_exit = solver.Value(train_vars[train_id]["exit_time"])

                if abs(entry_dev) > 0 or abs(exit_dev) > 0:
                    trains_adjusted += 1

                optimized_schedule[train_id] = {
                    "original_entry": modified_schedules[train_id]["entry_time"],
                    "original_exit": modified_schedules[train_id]["exit_time"],
                    "optimized_entry": optimized_entry,
                    "optimized_exit": optimized_exit,
                    "entry_deviation": entry_dev,
                    "exit_deviation": exit_dev,
                    "journey_time": optimized_exit - optimized_entry
                }

            result = {
                "status": "optimal" if status == cp_model.OPTIMAL else "feasible",
                "total_trains": len(valid_trains),
                "trains_adjusted": trains_adjusted,
                "total_deviation_minutes": total_deviation_value,
                "average_deviation": total_deviation_value / (2 * len(valid_trains)),
                "optimized_schedule": optimized_schedule,
                "solve_time_seconds": round(solve_time, 2),
                "constraints": {
                    "headway_constraints": headway_constraints,
                    "platform_constraints": platform_constraints,
                    "min_headway_minutes": self.min_headway
                },
                "scenario": scenario
            }

            self.logger.info(f"Optimization successful: {trains_adjusted} trains adjusted, total deviation: {total_deviation_value} minutes")
            return result

        else:
            self.logger.warning(f"Optimization failed with status: {solver.StatusName(status)}")
            return {
                "status": "failed",
                "reason": solver.StatusName(status),
                "total_trains": len(valid_trains),
                "solve_time_seconds": round(solve_time, 2),
                "scenario": scenario
            }

    def _apply_scenario(self, schedules: Dict, scenario: str) -> Dict:
        """Apply scenario-specific modifications to schedules"""
        modified = schedules.copy()

        if scenario == 'weather_disruption':
            # Add random delays to simulate weather impact
            for train_id in modified:
                # Weather typically affects entry times more
                modified[train_id] = modified[train_id].copy()

        elif scenario == 'add_delay':
            # Add significant delay to first train
            first_train = list(modified.keys())[0]
            modified[first_train] = modified[first_train].copy()
            # Delay will be added in constraints

        elif scenario == 'reduce_headway':
            # No schedule modifications needed - constraint change only
            pass

        return modified

    def calculate_section_throughput(self, optimized_schedule: Dict) -> Dict:
        """Calculate throughput metrics from optimized schedule"""
        if not optimized_schedule:
            return {"throughput_per_hour": 0, "average_headway": 0}

        entry_times = [data["optimized_entry"] for data in optimized_schedule.values()]
        entry_times.sort()

        if len(entry_times) < 2:
            return {"throughput_per_hour": 0, "average_headway": 0}

        # Calculate time span and throughput
        time_span_minutes = entry_times[-1] - entry_times[0]
        if time_span_minutes > 0:
            throughput_per_hour = (len(entry_times) / time_span_minutes) * 60
        else:
            throughput_per_hour = 0

        # Calculate average headway
        headways = [entry_times[i+1] - entry_times[i] for i in range(len(entry_times)-1)]
        average_headway = sum(headways) / len(headways) if headways else 0

        return {
            "throughput_per_hour": round(throughput_per_hour, 2),
            "average_headway": round(average_headway, 1),
            "min_headway": min(headways) if headways else 0,
            "max_headway": max(headways) if headways else 0
        }

    def generate_recommendations(self, optimization_result: Dict) -> List[str]:
        """Generate actionable recommendations based on optimization results"""
        recommendations = []

        if optimization_result.get("status") == "optimal":
            trains_adjusted = optimization_result.get("trains_adjusted", 0)
            total_deviation = optimization_result.get("total_deviation_minutes", 0)

            if trains_adjusted == 0:
                recommendations.append("✅ Current schedule is optimal - no adjustments needed")
            elif total_deviation < 30:
                recommendations.append(f"✅ Minor adjustments to {trains_adjusted} trains improve efficiency")
            else:
                recommendations.append(f"⚠️ Significant adjustments needed: {trains_adjusted} trains, {total_deviation}min total deviation")

            # Throughput recommendations
            throughput_data = self.calculate_section_throughput(optimization_result.get("optimized_schedule", {}))
            throughput = throughput_data.get("throughput_per_hour", 0)

            if throughput > 6:
                recommendations.append("🚀 High throughput achieved - monitor for bottlenecks")
            elif throughput < 2:
                recommendations.append("📈 Low throughput - consider increasing frequency or reducing delays")

            # Headway recommendations
            avg_headway = throughput_data.get("average_headway", 0)
            if avg_headway < 5:
                recommendations.append("⚠️ Headway below 5 minutes - ensure safety protocols")
            elif avg_headway > 20:
                recommendations.append("💡 Large headway gaps - opportunity to add more services")

        elif optimization_result.get("status") == "failed":
            recommendations.append("❌ Optimization failed - review constraints and data quality")
            recommendations.append("🔧 Consider relaxing constraints or updating train priorities")

        return recommendations
