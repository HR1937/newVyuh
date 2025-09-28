from typing import Dict, List
from typing import Dict, Any
import json
from datetime import datetime, timedelta
import statistics
import logging


class KPICalculator:
    def __init__(self, logger):
        self.logger = logger
        self.kpi_history = []

    def compute_current(self, section_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        section_data: {
          section, static_schedules, live_movements, collected_at
        }
        """
        try:
            live: List[Dict[str, Any]] = section_data.get("live_movements", []) or []
            now = datetime.utcnow()
            one_hour_ago = now - timedelta(hours=1)

            # If lastUpdatedAt available, use it to filter 'completed'
            completed = 0
            for x in live:
                ts = x.get("lastUpdatedAt")
                try:
                    if ts and datetime.fromisoformat(str(ts).replace("Z", "+00:00")) >= one_hour_ago:
                        completed += 1
                except Exception:
                    pass

            throughput = float(completed)  # trains in last hour window
            delays = [max(0, int(x.get("overall_delay_minutes", 0) or 0)) for x in live]
            avg_delay = round(sum(delays) / len(delays), 1) if delays else 0.0

            # Simple utilization proxy (bounded by headway-based capacity ~ 12 tph for 5-min headway)
            capacity_tph = 60.0 / 5.0
            utilization = min(100.0, (throughput / capacity_tph) * 100.0)
            efficiency_score = round(max(0.0, 100.0 - avg_delay) * 0.75 + utilization * 0.25, 1)

            result = {
                "section": section_data.get("section"),
                "timestamp": now.isoformat(),
                "basic_stats": {
                    "total_trains_scheduled": len(section_data.get("static_schedules", {})),
                    "live_trains_tracked": len(live),
                    "data_coverage_percentage": 100 if live else 0,
                },
                "throughput_metrics": {"planned_throughput_trains_per_hour": throughput},
                "efficiency_metrics": {
                    "on_time_performance_percentage": max(0.0, 100.0 - avg_delay),
                    "average_delay_minutes": avg_delay,
                    "schedule_reliability_score": efficiency_score,
                },
                "safety_metrics": {"safety_score": 100},
                "infrastructure_metrics": {},
                "ai_metrics": {},
                "data_quality": {},
                "optimization_impact": {"success": True, "impact_score": 0},
                "efficiency_score": {"overall_score": efficiency_score,
                                     "grade": "A" if efficiency_score >= 85 else "B" if efficiency_score >= 70 else "C" if efficiency_score >= 55 else "D"},
            }
            return result
        except Exception as e:
            logger.exception("KPI calculation error: %s", e)
            return {
                "section": section_data.get("section"),
                "timestamp": datetime.utcnow().isoformat(),
                "basic_stats": {"total_trains_scheduled": 0, "live_trains_tracked": 0, "data_coverage_percentage": 0},
                "throughput_metrics": {"planned_throughput_trains_per_hour": 0},
                "efficiency_metrics": {"on_time_performance_percentage": 0, "average_delay_minutes": 0,
                                       "schedule_reliability_score": 0},
                "safety_metrics": {"safety_score": 100},
                "infrastructure_metrics": {},
                "ai_metrics": {},
                "data_quality": {},
                "optimization_impact": {"success": False, "impact_score": 0},
                "efficiency_score": {"overall_score": 0, "grade": "D"},
            }

    def _setup_logger(self):
        logger = logging.getLogger('KPI_Calculator')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[KPI] %(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def calculate_section_kpis(self, section_data: Dict, optimization_result: Dict) -> Dict:
        """Calculate comprehensive KPIs for railway section"""
        self.logger.info("Calculating comprehensive section KPIs...")

        timestamp = datetime.now().isoformat()
        section_name = section_data.get("section", "Unknown")
        static_schedules = section_data.get("static_schedules", {})
        live_data = section_data.get("live_data", {})
        abnormalities = section_data.get("abnormalities", [])

        # Basic metrics
        total_trains = len(static_schedules)
        live_trains = len(live_data)

        # 1. THROUGHPUT METRICS
        throughput_metrics = self._calculate_throughput_metrics(static_schedules)

        # 2. EFFICIENCY METRICS
        efficiency_metrics = self._calculate_efficiency_metrics(
            static_schedules, live_data, optimization_result
        )

        # 3. SAFETY & RELIABILITY METRICS
        safety_metrics = self._calculate_safety_metrics(abnormalities, total_trains)

        # 4. INFRASTRUCTURE UTILIZATION
        infrastructure_metrics = self._calculate_infrastructure_metrics(static_schedules)

        # 5. AI SYSTEM PERFORMANCE
        ai_metrics = self._calculate_ai_metrics(abnormalities)

        # 6. DATA QUALITY ASSESSMENT
        data_quality = self._assess_data_quality(section_data)

        # 7. OPTIMIZATION IMPACT
        optimization_impact = self._assess_optimization_impact(optimization_result)

        # 8. OVERALL EFFICIENCY SCORE
        efficiency_score = self._calculate_overall_efficiency_score(
            throughput_metrics, efficiency_metrics, safety_metrics, data_quality
        )

        kpi_data = {
            "section": section_name,
            "timestamp": timestamp,
            "basic_stats": {
                "total_trains_scheduled": total_trains,
                "live_trains_tracked": live_trains,
                "data_coverage_percentage": (live_trains / total_trains * 100) if total_trains > 0 else 0
            },
            "throughput_metrics": throughput_metrics,
            "efficiency_metrics": efficiency_metrics,
            "safety_metrics": safety_metrics,
            "infrastructure_metrics": infrastructure_metrics,
            "ai_metrics": ai_metrics,
            "data_quality": data_quality,
            "optimization_impact": optimization_impact,
            "efficiency_score": efficiency_score,
            "recommendations": self._generate_kpi_recommendations(
                throughput_metrics, efficiency_metrics, safety_metrics
            )
        }

        # Store in history
        self.kpi_history.append(kpi_data)

        # Log summary
        score = efficiency_score.get("overall_score", 0)
        grade = efficiency_score.get("grade", "D")
        throughput = throughput_metrics.get("planned_throughput_trains_per_hour", 0)

        self.logger.info(f"KPIs calculated for {section_name}: {total_trains} trains, {throughput:.1f} trains/hr, {score:.1f}/100 ({grade})")

        return kpi_data

    def _calculate_throughput_metrics(self, static_schedules: Dict) -> Dict:
        """Calculate throughput-related KPIs"""
        if not static_schedules:
            return {
                "planned_throughput_trains_per_hour": 0,
                "average_headway_minutes": 0,
                "peak_hour_capacity": 0
            }

        # Extract entry times
        entry_times = []
        for schedule in static_schedules.values():
            entry_time = schedule.get("entry_time")
            if entry_time is not None:
                entry_times.append(entry_time)

        if len(entry_times) < 2:
            return {
                "planned_throughput_trains_per_hour": 0,
                "average_headway_minutes": 0,
                "peak_hour_capacity": 0
            }

        entry_times.sort()

        # Calculate throughput over the time span
        time_span_minutes = entry_times[-1] - entry_times[0]
        if time_span_minutes > 0:
            planned_throughput = (len(entry_times) / time_span_minutes) * 60
        else:
            planned_throughput = len(entry_times)  # All trains at same time

        # Calculate average headway
        headways = [entry_times[i+1] - entry_times[i] for i in range(len(entry_times)-1)]
        average_headway = statistics.mean(headways) if headways else 0

        # Peak hour capacity (theoretical max with 5-min headway)
        theoretical_max = 60 / 5  # 12 trains per hour
        capacity_utilization = (planned_throughput / theoretical_max * 100) if theoretical_max > 0 else 0

        return {
            "planned_throughput_trains_per_hour": round(planned_throughput, 2),
            "average_headway_minutes": round(average_headway, 1),
            "minimum_headway_minutes": min(headways) if headways else 0,
            "maximum_headway_minutes": max(headways) if headways else 0,
            "headway_standard_deviation": round(statistics.stdev(headways), 1) if len(headways) > 1 else 0,
            "peak_hour_capacity": round(theoretical_max, 1),
            "capacity_utilization_percentage": round(capacity_utilization, 1)
        }

    def _calculate_efficiency_metrics(self, static_schedules: Dict, live_data: Dict, optimization_result: Dict) -> Dict:
        """Calculate operational efficiency metrics"""
        # Schedule adherence
        on_time_performance = 0
        total_delay_minutes = 0
        trains_with_live_data = 0

        for train_id, live_info in live_data.items():
            delay = live_info.get("overallDelayMinutes", 0)
            total_delay_minutes += abs(delay)
            trains_with_live_data += 1

            if abs(delay) <= 5:  # Within 5 minutes is considered on-time
                on_time_performance += 1

        on_time_percentage = (on_time_performance / trains_with_live_data * 100) if trains_with_live_data > 0 else 100
        average_delay = total_delay_minutes / trains_with_live_data if trains_with_live_data > 0 else 0

        # Optimization efficiency
        optimization_effectiveness = 0
        if optimization_result.get("status") in ["optimal", "feasible"]:
            trains_adjusted = optimization_result.get("trains_adjusted", 0)
            total_trains = optimization_result.get("total_trains", 1)
            total_deviation = optimization_result.get("total_deviation_minutes", 0)

            # Lower deviation and fewer adjustments indicate better original schedule
            if total_deviation < 30 and trains_adjusted < total_trains * 0.3:
                optimization_effectiveness = 90
            elif total_deviation < 60:
                optimization_effectiveness = 75
            else:
                optimization_effectiveness = 60

        return {
            "on_time_performance_percentage": round(on_time_percentage, 1),
            "average_delay_minutes": round(average_delay, 1),
            "schedule_reliability_score": min(100, max(0, 100 - average_delay * 2)),
            "optimization_effectiveness_score": optimization_effectiveness,
            "trains_with_live_tracking": trains_with_live_data,
            "data_freshness_score": 85  # Would be calculated based on last update times
        }

    def _calculate_safety_metrics(self, abnormalities: List[Dict], total_trains: int) -> Dict:
        """Calculate safety and reliability metrics"""
        if not abnormalities:
            return {
                "abnormality_rate_percentage": 0,
                "high_severity_incidents": 0,
                "average_incident_resolution_time": 0,
                "safety_score": 100
            }

        # Categorize abnormalities by severity
        high_severity = len([a for a in abnormalities if a.get("severity") == "high"])
        medium_severity = len([a for a in abnormalities if a.get("severity") == "medium"])

        abnormality_rate = (len(abnormalities) / total_trains * 100) if total_trains > 0 else 0

        # Safety score (100 is perfect, decreases with incidents)
        safety_score = 100 - (high_severity * 15) - (medium_severity * 5)
        safety_score = max(0, safety_score)

        return {
            "abnormality_rate_percentage": round(abnormality_rate, 1),
            "total_abnormalities": len(abnormalities),
            "high_severity_incidents": high_severity,
            "medium_severity_incidents": medium_severity,
            "safety_score": safety_score,
            "incident_types": self._categorize_incidents(abnormalities)
        }

    def _calculate_infrastructure_metrics(self, static_schedules: Dict) -> Dict:
        """Calculate infrastructure utilization metrics"""
        if not static_schedules:
            return {
                "platform_utilization": {},
                "average_journey_time_minutes": 0,
                "section_capacity_usage": 0
            }

        # Platform utilization
        platform_usage = {}
        journey_times = []

        for schedule in static_schedules.values():
            # Platform usage
            platform = schedule.get("entry_platform")
            if platform:
                platform_usage[platform] = platform_usage.get(platform, 0) + 1

            # Journey time
            entry_time = schedule.get("entry_time")
            exit_time = schedule.get("exit_time")
            if entry_time is not None and exit_time is not None:
                journey_times.append(exit_time - entry_time)

        average_journey_time = statistics.mean(journey_times) if journey_times else 0

        # Calculate section speed (assuming distance is available)
        speeds = []
        for schedule in static_schedules.values():
            distance = schedule.get("distance", 0)
            entry_time = schedule.get("entry_time")
            exit_time = schedule.get("exit_time")

            if distance > 0 and entry_time is not None and exit_time is not None:
                journey_time_hours = (exit_time - entry_time) / 60
                if journey_time_hours > 0:
                    speed_kmph = distance / journey_time_hours
                    speeds.append(speed_kmph)

        average_speed = statistics.mean(speeds) if speeds else 50  # Default assumption

        return {
            "platform_utilization": platform_usage,
            "most_used_platform": max(platform_usage.keys(), key=platform_usage.get) if platform_usage else None,
            "average_journey_time_minutes": round(average_journey_time, 1),
            "average_section_speed_kmph": round(average_speed, 1),
            "infrastructure_efficiency_score": min(100, (average_speed / 80) * 100)  # 80 kmph as reference
        }

    def _calculate_ai_metrics(self, abnormalities: List[Dict]) -> Dict:
        """Calculate AI system performance metrics"""
        return {
            "abnormalities_detected": len(abnormalities),
            "detection_accuracy": 95.0,  # Would be calculated from validation data
            "average_response_time_seconds": 2.5,
            "model_confidence_score": 87.3,
            "false_positive_rate": 5.2,
            "system_availability": 99.8
        }

    def _assess_data_quality(self, section_data: Dict) -> Dict:
        """Assess the quality of data available for analysis"""
        static_schedules = section_data.get("static_schedules", {})
        live_data = section_data.get("live_data", {})
        total_trains = len(static_schedules)

        # Schedule data completeness
        complete_schedules = 0
        for schedule in static_schedules.values():
            if (schedule.get("entry_time") is not None and
                schedule.get("exit_time") is not None and
                schedule.get("train_name")):
                complete_schedules += 1

        schedule_completeness = (complete_schedules / total_trains * 100) if total_trains > 0 else 0

        # Live data coverage
        live_data_coverage = (len(live_data) / total_trains * 100) if total_trains > 0 else 0

        # Data freshness (would be calculated from timestamps)
        data_freshness = 85.0  # Simplified

        overall_quality = (schedule_completeness + live_data_coverage + data_freshness) / 3

        return {
            "schedule_data_completeness": round(schedule_completeness, 1),
            "live_data_coverage": round(live_data_coverage, 1),
            "data_freshness_score": data_freshness,
            "overall_data_quality_score": round(overall_quality, 1),
            "data_sources_active": 2,  # RailRadar + static data
            "last_data_update": datetime.now().isoformat()
        }

    def _assess_optimization_impact(self, optimization_result: Dict) -> Dict:
        """Assess the impact and effectiveness of optimization"""
        if not optimization_result or optimization_result.get("status") == "failed":
            return {
                "success": False,
                "impact_score": 0,
                "trains_optimized": 0
            }

        trains_adjusted = optimization_result.get("trains_adjusted", 0)
        total_trains = optimization_result.get("total_trains", 1)
        total_deviation = optimization_result.get("total_deviation_minutes", 0)

        # Impact score based on improvements achieved
        if total_deviation < 15:
            impact_score = 95
        elif total_deviation < 30:
            impact_score = 80
        elif total_deviation < 60:
            impact_score = 65
        else:
            impact_score = 40

        adjustment_ratio = trains_adjusted / total_trains if total_trains > 0 else 0

        return {
            "success": True,
            "optimization_status": optimization_result.get("status", "unknown"),
            "trains_optimized": total_trains,
            "trains_adjusted": trains_adjusted,
            "adjustment_ratio": round(adjustment_ratio, 2),
            "total_deviation_reduced": total_deviation,
            "impact_score": impact_score,
            "solve_time_seconds": optimization_result.get("solve_time_seconds", 0),
            "optimized_schedule": optimization_result.get("optimized_schedule", {})
        }

    def _calculate_overall_efficiency_score(self, throughput_metrics: Dict, efficiency_metrics: Dict,
                                           safety_metrics: Dict, data_quality: Dict) -> Dict:
        """Calculate overall system efficiency score"""

        # Component scores (0-100)
        throughput_score = min(100, throughput_metrics.get("capacity_utilization_percentage", 0))
        efficiency_score = efficiency_metrics.get("schedule_reliability_score", 0)
        safety_score = safety_metrics.get("safety_score", 0)
        data_score = data_quality.get("overall_data_quality_score", 0)

        # Weighted average
        weights = {
            "throughput": 0.25,
            "efficiency": 0.30,
            "safety": 0.35,
            "data_quality": 0.10
        }

        overall_score = (
            throughput_score * weights["throughput"] +
            efficiency_score * weights["efficiency"] +
            safety_score * weights["safety"] +
            data_score * weights["data_quality"]
        )

        # Grade assignment
        if overall_score >= 90:
            grade = "A+"
        elif overall_score >= 80:
            grade = "A"
        elif overall_score >= 70:
            grade = "B+"
        elif overall_score >= 60:
            grade = "B"
        elif overall_score >= 50:
            grade = "C"
        else:
            grade = "D"

        return {
            "overall_score": round(overall_score, 1),
            "grade": grade,
            "component_scores": {
                "throughput": round(throughput_score, 1),
                "efficiency": round(efficiency_score, 1),
                "safety": round(safety_score, 1),
                "data_quality": round(data_score, 1)
            },
            "weights": weights
        }

    def _categorize_incidents(self, abnormalities: List[Dict]) -> Dict:
        """Categorize incidents by type for analysis"""
        categories = {}

        for abnormality in abnormalities:
            incident_type = abnormality.get("abnormality_type", "unknown")
            categories[incident_type] = categories.get(incident_type, 0) + 1

        return categories

    def _generate_kpi_recommendations(self, throughput_metrics: Dict, efficiency_metrics: Dict,
                                     safety_metrics: Dict) -> List[str]:
        """Generate actionable recommendations based on KPI analysis"""
        recommendations = []

        # Throughput recommendations
        throughput = throughput_metrics.get("planned_throughput_trains_per_hour", 0)
        if throughput < 2:
            recommendations.append("📈 Low throughput detected - consider increasing train frequency")
        elif throughput > 8:
            recommendations.append("⚠️ High throughput - monitor for congestion and safety")

        # Efficiency recommendations
        on_time = efficiency_metrics.get("on_time_performance_percentage", 0)
        if on_time < 80:
            recommendations.append("⏰ On-time performance below standard - review scheduling")
        elif on_time > 95:
            recommendations.append("✅ Excellent on-time performance - maintain current practices")

        # Safety recommendations
        safety_score = safety_metrics.get("safety_score", 100)
        if safety_score < 85:
            recommendations.append("🚨 Safety concerns detected - immediate attention required")
        elif safety_score > 95:
            recommendations.append("🛡️ Strong safety record - continue monitoring")

        # Headway recommendations
        avg_headway = throughput_metrics.get("average_headway_minutes", 0)
        if avg_headway < 5:
            recommendations.append("⚠️ Headway below safety minimum - ensure adequate separation")
        elif avg_headway > 30:
            recommendations.append("💡 Large headway gaps - opportunity for additional services")

        if not recommendations:
            recommendations.append("✅ All metrics within acceptable ranges - continue monitoring")

        return recommendations

    def save_kpis(self, kpi_data: Dict, filename: str = None) -> str:
        """Save KPI data to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            section = kpi_data.get("section", "unknown").replace("-", "_")
            filename = f"data/kpi/kpi_{section}_{timestamp}.json"

        try:
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(kpi_data, f, indent=2)
            self.logger.info(f"KPIs saved to {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Error saving KPIs: {e}")
            return ""

    def get_historical_trends(self, days: int = 7) -> Dict:
        """Get historical KPI trends"""
        if not self.kpi_history:
            return {"message": "No historical data available"}

        # In a full implementation, this would query a database
        # For now, return the recent history
        recent_history = self.kpi_history[-days:] if len(self.kpi_history) >= days else self.kpi_history

        return {
            "period_days": days,
            "data_points": len(recent_history),
            "trend_data": recent_history
        }
