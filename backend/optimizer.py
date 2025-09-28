import logging
from ortools.sat.python import cp_model
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from backend.config import Config


class TrainScheduleOptimizer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def optimize_scenario(self, scenario, trains, ways):
        """Use CP-SAT to select 2 best solutions per way, maximize throughput"""
        model = cp_model.CpModel()
        solutions = []
        for way in ways:
            # Dummy trains list (from live/static), assume trains = [{'num':, 'time':, 'priority':}]
            # Variables: For each train, assign new time/speed/track
            time_vars = {}
            for train in trains:
                # Fix: Use string name, not expression
                time_vars[train['num']] = model.NewIntVar(0, 1440, f"time_{train['num']}")  # Minutes in day
                # Safety constraints
                for other in trains:
                    if train != other:
                        headway = abs(time_vars[train['num']] - time_vars[other['num']])
                        model.Add(headway >= Config.MIN_HEADWAY_MINUTES)
                model.Add(time_vars[train['num']] - train['original_time'] <= Config.MAX_DEVIATION_MINUTES)

            # Objective: Maximize throughput (min total time for all trains)
            total_time = sum(time_vars.values())
            model.Minimize(total_time)  # Inverse for throughput

            solver = cp_model.CpSolver()
            status = solver.Solve(model)
            if status == cp_model.OPTIMAL:
                # Get 2 solutions (use solver parameters for multiple, but simplify to one + variant)
                sol1 = {t['num']: solver.Value(time_vars[t['num']]) for t in trains}
                kpi1 = self.calculate_kpi(sol1, trains)  # Throughput, etc.
                # Variant: Add slight change for second
                model.Add(total_time >= solver.ObjectiveValue() + 1)  # Suboptimal
                status = solver.Solve(model)
                sol2 = {t['num']: solver.Value(time_vars[t['num']]) for t in trains} if status == cp_model.OPTIMAL else sol1
                kpi2 = self.calculate_kpi(sol2, trains)
                solutions.extend([{'way': way, 'sol': sol1, 'kpi': kpi1, 'priority': 1}, {'way': way, 'sol': sol2, 'kpi': kpi2, 'priority': 2}])
            else:
                self.logger.error(f"Optimization failed for {scenario}: {status}")
        # Sort by KPI (throughput desc)
        solutions.sort(key=lambda s: s['kpi']['throughput'], reverse=True)
        return solutions

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
        self.logger.info(f"Starting optimization for scenario: {scenario}")

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

        modified_schedules = self._apply_scenario(valid_trains, scenario)

        model = cp_model.CpModel()
        solver = cp_model.CpSolver()

        train_vars = {}
        deviation_vars = {}

        for train_id, schedule in modified_schedules.items():
            original_entry = schedule["entry_time"]
            original_exit = schedule["exit_time"]

            max_deviation = 120  # ±2 hours

            entry_deviation = model.NewIntVar(-max_deviation, max_deviation, f"entry_dev_{train_id}")
            exit_deviation = model.NewIntVar(-max_deviation, max_deviation, f"exit_dev_{train_id}")

            entry_time = model.NewIntVar(0, 1440, f"entry_{train_id}")
            exit_time = model.NewIntVar(0, 1440, f"exit_{train_id}")

            model.Add(entry_time == original_entry + entry_deviation)
            model.Add(exit_time == original_exit + exit_deviation)

            journey_time = original_exit - original_entry
            model.Add(exit_time >= entry_time + max(journey_time // 2, 15))

            train_vars[train_id] = {
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_deviation": entry_deviation,
                "exit_deviation": exit_deviation
            }
            deviation_vars[train_id] = (entry_deviation, exit_deviation)

        # Scenario-adjusted headway
        min_headway_local = 3 if scenario == 'reduce_headway' else self.min_headway  #

        train_list = list(modified_schedules.keys())
        headway_constraints = 0
        platform_constraints = 0

        for i in range(len(train_list)):
            for j in range(i + 1, len(train_list)):
                a = train_list[i]
                b = train_list[j]

                # Precedence booleans
                a_before_b = model.NewBoolVar(f"{a}_before_{b}")
                b_before_a = model.NewBoolVar(f"{b}_before_{a}")
                model.Add(a_before_b + b_before_a == 1)

                # Headway precedence constraints
                model.Add(train_vars[a]["entry_time"] + min_headway_local <= train_vars[b]["entry_time"]).OnlyEnforceIf(
                    a_before_b)
                model.Add(train_vars[b]["entry_time"] + min_headway_local <= train_vars[a]["entry_time"]).OnlyEnforceIf(
                    b_before_a)
                headway_constraints += 2

                # Platform separation if same platform
                platform_a = modified_schedules[a].get("entry_platform")
                platform_b = modified_schedules[b].get("entry_platform")
                if platform_a and platform_b and platform_a == platform_b:
                    model.Add(train_vars[a]["entry_time"] + 10 <= train_vars[b]["entry_time"]).OnlyEnforceIf(a_before_b)
                    model.Add(train_vars[b]["entry_time"] + 10 <= train_vars[a]["entry_time"]).OnlyEnforceIf(b_before_a)
                    platform_constraints += 2

        # Scenario-specific constraints
        if scenario == 'weather_disruption':
            for train_id in train_vars:
                model.Add(deviation_vars[train_id][0] >= 10)  # >= 10 min delay on entry
        elif scenario == 'add_delay':
            first_train = train_list[0]
            model.Add(deviation_vars[first_train][0] >= 20)

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

        start_time = datetime.now()
        solver.parameters.max_time_in_seconds = 30

        status = solver.Solve(model)
        solve_time = (datetime.now() - start_time).total_seconds()

        self.logger.info(
            f"Model created: {len(valid_trains)} trains, {headway_constraints} headway cons, {platform_constraints} platform cons")

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            optimized_schedule = {}
            total_deviation_value = solver.Value(total_deviation)
            trains_adjusted = 0

            for train_id in train_vars:
                entry_dev_val = solver.Value(deviation_vars[train_id][0])
                exit_dev_val = solver.Value(deviation_vars[train_id][1])
                optimized_entry = solver.Value(train_vars[train_id]["entry_time"])
                optimized_exit = solver.Value(train_vars[train_id]["exit_time"])

                if abs(entry_dev_val) > 0 or abs(exit_dev_val) > 0:
                    trains_adjusted += 1

                optimized_schedule[train_id] = {
                    "original_entry": modified_schedules[train_id]["entry_time"],
                    "original_exit": modified_schedules[train_id]["exit_time"],
                    "optimized_entry": optimized_entry,
                    "optimized_exit": optimized_exit,
                    "entry_deviation": entry_dev_val,
                    "exit_deviation": exit_dev_val,
                    "journey_time": optimized_exit - optimized_entry
                }

            return {
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
                    "min_headway_minutes": min_headway_local
                },
                "scenario": scenario
            }
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

    def _get_scenario_adjustments(self, scenario):
        """Get adjustments for different scenarios"""
        adjustments = {
            "default": {"delay_offset": 0, "headway_multiplier": 1.0},
            "reduce_headway": {"delay_offset": 0, "headway_multiplier": 0.6},
            "weather_disruption": {"delay_offset": 15, "headway_multiplier": 1.2},
            "add_delay": {"delay_offset": 30, "headway_multiplier": 1.0},
            "emergency": {"delay_offset": 45, "headway_multiplier": 1.5}
        }
        return adjustments.get(scenario, adjustments["default"])

    def calculate_kpi(self, solution, trains):
        """Calculate KPIs: throughput = trains / max_time, efficiency = (target - delay)/target *100"""
        max_time = max(solution.values()) / 60.0  # hours
        throughput = len(trains) / max_time if max_time > 0 else 0
        avg_delay = sum(abs(v - t['original_time']) for t, v in solution.items()) / len(trains)
        efficiency = max(0, Config.EFFICIENCY_TARGET_SCORE - avg_delay)
        return {'throughput': throughput, 'efficiency': efficiency, 'avg_delay': avg_delay}

    def run_what_if(self, scenario='reduce_headway'):
        # Mock past data trains
        trains = [{'num': '12345', 'original_time': 600, 'priority': 1}]  # From past_data
        ways = ['change_track', 'speed_adjustment']  # Based on scenario
        solutions = self.optimize_scenario(scenario, trains, ways)
        return solutions  # With KPI impact