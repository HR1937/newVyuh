import logging
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class TrainScheduleOptimizer:
    def __init__(self, min_headway_minutes: int = 5):
        self.min_headway = min_headway_minutes
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger('Optimizer')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[OPT] %(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def optimize_section_schedule(self, static_schedules: Dict, scenario: str = 'default') -> Dict:
        try:
            self.logger.info(f"Starting schedule optimization (scenario: {scenario})")

            if not static_schedules:
                return {
                    "status": "no_data",
                    "message": "No schedules provided for optimization",
                    "throughput": 0
                }

            model = cp_model.CpModel()
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30

            trains = list(static_schedules.keys())
            train_vars = {}
            deviation_vars = {}
            throughput_vars = {}

            for train_id in trains:
                original_time = static_schedules[train_id].get('entry_time', 360)

                deviation_vars[train_id] = model.NewIntVar(
                    -60, 60, f'deviation_{train_id}'
                )

                train_vars[train_id] = model.NewIntVar(
                    max(0, original_time - 60),
                    original_time + 60,
                    f'adjusted_time_{train_id}'
                )

                model.Add(train_vars[train_id] == original_time + deviation_vars[train_id])

                throughput_vars[train_id] = model.NewIntVar(0, 100, f'throughput_{train_id}')

            sorted_trains = sorted(trains, key=lambda t: static_schedules[t].get('entry_time', 360))

            for i in range(len(sorted_trains) - 1):
                train1 = sorted_trains[i]
                train2 = sorted_trains[i + 1]

                headway_satisfied = model.NewBoolVar(f'headway_{train1}_{train2}')

                headway_diff = train_vars[train2] - train_vars[train1]

                model.Add(headway_diff >= self.min_headway).OnlyEnforceIf(headway_satisfied)
                model.Add(headway_diff >= self.min_headway)

            if scenario == 'reduce_headway':
                for i, train_id in enumerate(trains):
                    if i > 0:
                        prev_train = trains[i - 1]
                        model.Add(deviation_vars[train_id] >= -30)
                        model.Add(deviation_vars[train_id] <= 30)

            elif scenario == 'maximize_throughput':
                total_throughput = model.NewIntVar(0, len(trains) * 100, 'total_throughput')
                model.Add(total_throughput == sum(throughput_vars.values()))

                for i, train_id in enumerate(trains):
                    if i > 0:
                        prev_train = trains[i - 1]
                        model.Add(throughput_vars[train_id] >= 70)
                    else:
                        model.Add(throughput_vars[train_id] >= 80)

                model.Maximize(total_throughput)

            elif scenario == 'minimize_delay':
                total_deviation = model.NewIntVar(
                    -len(trains) * 60,
                    len(trains) * 60,
                    'total_deviation'
                )
                model.Add(total_deviation == sum(deviation_vars.values()))

                abs_deviation_vars = {}
                for train_id in trains:
                    abs_dev = model.NewIntVar(0, 60, f'abs_dev_{train_id}')
                    abs_deviation_vars[train_id] = abs_dev

                    is_positive = model.NewBoolVar(f'pos_{train_id}')
                    model.Add(deviation_vars[train_id] >= 0).OnlyEnforceIf(is_positive)
                    model.Add(deviation_vars[train_id] < 0).OnlyEnforceIf(is_positive.Not())

                    model.Add(abs_dev == deviation_vars[train_id]).OnlyEnforceIf(is_positive)
                    model.Add(abs_dev == -deviation_vars[train_id]).OnlyEnforceIf(is_positive.Not())

                model.Minimize(sum(abs_deviation_vars.values()))

            else:
                total_throughput = model.NewIntVar(0, len(trains) * 100, 'total_throughput')
                model.Add(total_throughput == sum(throughput_vars.values()))

                total_abs_deviation = model.NewIntVar(0, len(trains) * 60, 'total_abs_dev')

                abs_vars = []
                for train_id in trains:
                    abs_dev = model.NewIntVar(0, 60, f'abs_dev_{train_id}')
                    is_positive = model.NewBoolVar(f'pos_{train_id}')

                    model.Add(deviation_vars[train_id] >= 0).OnlyEnforceIf(is_positive)
                    model.Add(deviation_vars[train_id] < 0).OnlyEnforceIf(is_positive.Not())
                    model.Add(abs_dev == deviation_vars[train_id]).OnlyEnforceIf(is_positive)
                    model.Add(abs_dev == -deviation_vars[train_id]).OnlyEnforceIf(is_positive.Not())

                    abs_vars.append(abs_dev)

                model.Add(total_abs_deviation == sum(abs_vars))

                objective = total_throughput * 10 - total_abs_deviation
                model.Maximize(objective)

            status = solver.Solve(model)

            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                optimized_schedules = {}
                total_deviation = 0
                trains_adjusted = 0

                for train_id in trains:
                    original_time = static_schedules[train_id].get('entry_time', 360)
                    deviation = solver.Value(deviation_vars[train_id])
                    adjusted_time = solver.Value(train_vars[train_id])

                    if abs(deviation) > 0:
                        trains_adjusted += 1

                    total_deviation += abs(deviation)

                    optimized_schedules[train_id] = {
                        **static_schedules[train_id],
                        'optimized_entry_time': adjusted_time,
                        'deviation_minutes': deviation,
                        'throughput_score': solver.Value(
                            throughput_vars[train_id]) if train_id in throughput_vars else 75
                    }

                if trains:
                    time_span_hours = (max(solver.Value(train_vars[t]) for t in trains) -
                                       min(solver.Value(train_vars[t]) for t in trains)) / 60
                    throughput = len(trains) / max(time_span_hours, 1)
                else:
                    throughput = 0

                result = {
                    "status": solver.StatusName(status).lower(),
                    "optimized_schedules": optimized_schedules,
                    "trains_adjusted": trains_adjusted,
                    "total_deviation_minutes": total_deviation,
                    "throughput": round(throughput, 2),
                    "objective_value": solver.ObjectiveValue(),
                    "solve_time_seconds": solver.WallTime(),
                    "scenario": scenario
                }

                self.logger.info(
                    f"Optimization successful: {trains_adjusted} trains adjusted, throughput: {throughput:.2f}")
                return result

            else:
                self.logger.error(f"Optimization failed: {solver.StatusName(status)}")
                return {
                    "status": "failed",
                    "error": f"Solver status: {solver.StatusName(status)}",
                    "throughput": 0,
                    "scenario": scenario
                }

        except Exception as e:
            self.logger.error(f"Optimization error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "throughput": 0,
                "scenario": scenario
            }

    def analyze_headway_feasibility(self, static_schedules: Dict) -> Dict:
        try:
            if not static_schedules:
                return {"feasible": True, "issues": []}

            trains = sorted(static_schedules.keys(),
                            key=lambda t: static_schedules[t].get('entry_time', 360))

            issues = []

            for i in range(len(trains) - 1):
                train1 = trains[i]
                train2 = trains[i + 1]

                time1 = static_schedules[train1].get('entry_time', 360)
                time2 = static_schedules[train2].get('entry_time', 360)

                headway = time2 - time1

                if headway < self.min_headway:
                    issues.append({
                        "trains": [train1, train2],
                        "current_headway": headway,
                        "required_headway": self.min_headway,
                        "adjustment_needed": self.min_headway - headway
                    })

            return {
                "feasible": len(issues) == 0,
                "issues": issues,
                "total_issues": len(issues)
            }

        except Exception as e:
            self.logger.error(f"Headway analysis error: {e}")
            return {"feasible": False, "error": str(e)}

    def generate_what_if_scenarios(self, static_schedules: Dict) -> Dict:
        try:
            scenarios = ['default', 'reduce_headway', 'maximize_throughput', 'minimize_delay']
            results = {}

            for scenario in scenarios:
                self.logger.info(f"Running what-if scenario: {scenario}")
                result = self.optimize_section_schedule(static_schedules, scenario)
                results[scenario] = result

            comparison = self._compare_scenarios(results)

            return {
                "scenario_results": results,
                "comparison": comparison,
                "recommendation": self._recommend_best_scenario(results)
            }

        except Exception as e:
            self.logger.error(f"What-if analysis error: {e}")
            return {"error": str(e)}

    def _compare_scenarios(self, results: Dict) -> Dict:
        comparison = {}

        for scenario, result in results.items():
            if result.get("status") in ["optimal", "feasible"]:
                comparison[scenario] = {
                    "throughput": result.get("throughput", 0),
                    "trains_adjusted": result.get("trains_adjusted", 0),
                    "total_deviation": result.get("total_deviation_minutes", 0),
                    "solve_time": result.get("solve_time_seconds", 0)
                }

        return comparison

    def _recommend_best_scenario(self, results: Dict) -> Dict:
        valid_results = {k: v for k, v in results.items()
                         if v.get("status") in ["optimal", "feasible"]}

        if not valid_results:
            return {"scenario": "none", "reason": "No valid optimization results"}

        scores = {}
        for scenario, result in valid_results.items():
            throughput = result.get("throughput", 0)
            deviation = result.get("total_deviation_minutes", 999)
            trains_adjusted = result.get("trains_adjusted", 0)

            score = (throughput * 10) - (deviation * 0.5) - (trains_adjusted * 2)
            scores[scenario] = score

        best_scenario = max(scores.keys(), key=lambda k: scores[k])

        return {
            "scenario": best_scenario,
            "score": scores[best_scenario],
            "reason": f"Best balance of throughput ({valid_results[best_scenario]['throughput']:.2f}) and minimal disruption",
            "all_scores": scores
        }

    def calculate_section_throughput(self, optimized_schedule: Dict) -> Dict:
        if not optimized_schedule:
            return {"throughput_per_hour": 0, "average_headway": 0}

        entry_times = [data["optimized_entry_time"] for data in optimized_schedule.values()]
        entry_times.sort()

        if len(entry_times) < 2:
            return {"throughput_per_hour": 0, "average_headway": 0}

        time_span_minutes = entry_times[-1] - entry_times[0]
        if time_span_minutes > 0:
            throughput_per_hour = (len(entry_times) / time_span_minutes) * 60
        else:
            throughput_per_hour = 0

        headways = [entry_times[i+1] - entry_times[i] for i in range(len(entry_times)-1)]
        average_headway = sum(headways) / len(headways) if headways else 0

        return {
            "throughput_per_hour": round(throughput_per_hour, 2),
            "average_headway": round(average_headway, 1),
            "min_headway": min(headways) if headways else 0,
            "max_headway": max(headways) if headways else 0
        }

    def generate_recommendations(self, optimization_result: Dict) -> List[str]:
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

            throughput_data = self.calculate_section_throughput(optimization_result.get("optimized_schedule", {}))
            throughput = throughput_data.get("throughput_per_hour", 0)

            if throughput > 6:
                recommendations.append("🚀 High throughput achieved - monitor for bottlenecks")
            elif throughput < 2:
                recommendations.append("📈 Low throughput - consider increasing frequency or reducing delays")

            avg_headway = throughput_data.get("average_headway", 0)
            if avg_headway < 5:
                recommendations.append("⚠️ Headway below safety minimum - ensure adequate separation")
            elif avg_headway > 20:
                recommendations.append("💡 Large headway gaps - opportunity for additional services")

        elif optimization_result.get("status") == "failed":
            recommendations.append("❌ Optimization failed - review constraints and data quality")
            recommendations.append("🔧 Consider relaxing constraints or updating train priorities")

        return recommendations
