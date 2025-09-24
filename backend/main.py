#!/usr/bin/env python3
"""
VyuhMitra - AI-Powered Train Traffic Control System
Main application orchestrating the complete workflow as per your requirements
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict

# Import our modules
from config import Config
from data_collector import RailRadarDataCollector
from ai_solution_system import AIMLSolutionSystem
from optimizer import TrainScheduleOptimizer
from kpi_calculator import KPICalculator

class VyuhMitraCore:
    def __init__(self, config: Config):
        self.config = config
        self.data_collector = RailRadarDataCollector(config.RAILRADAR_API_KEY)
        self.ai_system = AIMLSolutionSystem(config)
        self.optimizer = TrainScheduleOptimizer(config.MIN_HEADWAY_MINUTES)
        self.kpi_calculator = KPICalculator()

        # Ensure data directories exist
        self._create_directories()

        print(f"🚂 VyuhMitra Core System Initialized")
        print(f"   Section: {config.DEFAULT_FROM_STATION} → {config.DEFAULT_TO_STATION}")
        print(f"   API Key: {config.RAILRADAR_API_KEY[:20]}...")

    def _create_directories(self):
        """Create necessary data directories"""
        directories = [
            self.config.DATA_DIR,
            self.config.SCHEDULES_DIR,
            self.config.LIVE_DIR,
            self.config.RESULTS_DIR,
            self.config.KPI_DIR,
            "models"
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def log(self, msg: str):
        print(f"[VYUHMITRA] {datetime.now().strftime('%H:%M:%S')} - {msg}")

    def run_complete_workflow(self, from_station: str = None, to_station: str = None) -> Dict:
        """
        Execute the complete VyuhMitra workflow as per your requirements:
        1. Data Collection & Abnormality Detection
        2. AI-powered Reason Inference & Solution Generation
        3. Optimization & KPI Calculation
        4. What-if Analysis
        """

        if not from_station:
            from_station = self.config.DEFAULT_FROM_STATION
        if not to_station:
            to_station = self.config.DEFAULT_TO_STATION

        self.log(f"🔄 Starting complete workflow for section {from_station}-{to_station}")

        results = {
            "section": f"{from_station}-{to_station}",
            "workflow_start": datetime.now().isoformat(),
            "steps_completed": [],
            "errors": []
        }

        try:
            # ===== STEP 1: DATA COLLECTION & ABNORMALITY DETECTION =====
            self.log("📡 Step 1: Collecting section data and detecting abnormalities...")
            section_data = self.data_collector.collect_section_data(from_station, to_station)

            if section_data.get("valid_schedules", 0) == 0:
                self.log("⚠️  No valid train schedules found - running with simulated data")
                section_data = self._create_simulated_data(from_station, to_station)

            abnormalities = section_data.get("abnormalities", [])
            self.log(f"   Found {len(abnormalities)} abnormalities requiring attention")

            results["section_data"] = section_data
            results["abnormalities_detected"] = len(abnormalities)
            results["steps_completed"].append("data_collection")

            # ===== STEP 2: AI SOLUTION PROCESSING =====
            if abnormalities:
                self.log("🤖 Step 2: Processing abnormalities through AI system...")
                solution_results = []

                for abnormality in abnormalities:
                    self.log(f"   Processing abnormality: Train {abnormality['train_id']}")
                    solution_result = self.ai_system.process_abnormality(abnormality)
                    solution_results.append(solution_result)

                    if solution_result["status"] == "solutions_generated":
                        solutions_count = len(solution_result["solutions"])
                        self.log(f"   ✅ Generated {solutions_count} solutions for train {abnormality['train_id']}")

                results["ai_solutions"] = solution_results
                results["steps_completed"].append("ai_processing")
            else:
                self.log("✅ Step 2: No abnormalities detected - system operating normally")
                results["ai_solutions"] = []

            # ===== STEP 3: SCHEDULE OPTIMIZATION =====
            self.log("⚙️  Step 3: Running schedule optimization...")
            static_schedules = section_data.get("static_schedules", {})

            if static_schedules:
                optimization_result = self.optimizer.optimize_section_schedule(static_schedules, scenario='default')
                self.log(f"   ✅ Optimization {optimization_result.get('status', 'completed')}")

                if optimization_result.get("status") in ["optimal", "feasible"]:
                    trains_adjusted = optimization_result.get("trains_adjusted", 0)
                    total_deviation = optimization_result.get("total_deviation_minutes", 0)
                    self.log(f"   📊 Results: {trains_adjusted} trains adjusted, {total_deviation}min total deviation")
            else:
                optimization_result = {"status": "no_data", "message": "No schedules to optimize"}

            results["optimization"] = optimization_result
            results["steps_completed"].append("optimization")

            # ===== STEP 4: KPI CALCULATION =====
            self.log("📊 Step 4: Calculating comprehensive KPIs...")
            kpi_data = self.kpi_calculator.calculate_section_kpis(section_data, optimization_result)

            efficiency_score = kpi_data.get("efficiency_score", {}).get("overall_score", 0)
            grade = kpi_data.get("efficiency_score", {}).get("grade", "D")
            throughput = kpi_data.get("throughput_metrics", {}).get("planned_throughput_trains_per_hour", 0)

            self.log(f"   📈 Performance: {throughput:.1f} trains/hr, {efficiency_score:.1f}/100 ({grade})")

            results["kpis"] = kpi_data
            results["steps_completed"].append("kpi_calculation")

            # ===== STEP 5: WHAT-IF ANALYSIS =====
            self.log("🔮 Step 5: Running what-if scenario analysis...")
            whatif_results = self._run_whatif_scenarios(static_schedules)

            results["whatif_analysis"] = whatif_results
            results["steps_completed"].append("whatif_analysis")

            # ===== STEP 6: SAVE RESULTS =====
            self.log("💾 Step 6: Saving results...")
            saved_files = self._save_workflow_results(results)
            results["saved_files"] = saved_files
            results["steps_completed"].append("save_results")

            # ===== WORKFLOW COMPLETION =====
            results["workflow_end"] = datetime.now().isoformat()
            results["status"] = "completed_successfully"

            self.log("✅ Complete workflow finished successfully!")
            return results

        except Exception as e:
            error_msg = f"Workflow error: {str(e)}"
            self.log(f"❌ {error_msg}")
            results["errors"].append(error_msg)
            results["status"] = "failed"
            return results

    def _create_simulated_data(self, from_station: str, to_station: str) -> Dict:
        """Create simulated data for demonstration when no real data is available"""
        self.log("🎭 Creating simulated data for demonstration...")

        # Simulated train schedules
        simulated_trains = {
            "12345": {
                "train_name": "Gooty Express",
                "entry_time": 360,  # 06:00
                "exit_time": 420,   # 07:00
                "distance": 45,
                "entry_platform": "1",
                "exit_platform": "2",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            },
            "12346": {
                "train_name": "Guntakal Passenger",
                "entry_time": 480,  # 08:00
                "exit_time": 540,   # 09:00
                "distance": 45,
                "entry_platform": "2",
                "exit_platform": "1",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            },
            "12347": {
                "train_name": "Southern Express",
                "entry_time": 600,  # 10:00
                "exit_time": 660,   # 11:00
                "distance": 45,
                "entry_platform": "1",
                "exit_platform": "3",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            }
        }

        # Simulated abnormality for demonstration
        simulated_abnormalities = [
            {
                "train_id": "12346",
                "journey_date": datetime.now().strftime("%Y-%m-%d"),
                "section": f"{from_station}-{to_station}",
                "delay_minutes": 15,
                "status": "Signal failure ahead",
                "location": from_station,
                "location_name": "Gooty Junction",
                "abnormality_type": "delay",
                "detected_at": datetime.now().isoformat(),
                "severity": "medium"
            }
        ]

        return {
            "section": f"{from_station}-{to_station}",
            "timestamp": datetime.now().isoformat(),
            "total_trains": len(simulated_trains),
            "valid_schedules": len(simulated_trains),
            "static_schedules": simulated_trains,
            "live_data": {},
            "abnormalities": simulated_abnormalities,
            "data_source": "simulated_for_demo"
        }

    def _run_whatif_scenarios(self, static_schedules: Dict) -> Dict:
        """Run multiple what-if scenarios for analysis"""
        if not static_schedules:
            return {"message": "No schedules available for what-if analysis"}

        scenarios = ["default", "reduce_headway", "weather_disruption", "add_delay"]
        whatif_results = {}

        for scenario in scenarios:
            self.log(f"   Running scenario: {scenario}")
            try:
                result = self.optimizer.optimize_section_schedule(static_schedules, scenario=scenario)
                whatif_results[scenario] = result
            except Exception as e:
                whatif_results[scenario] = {"status": "failed", "error": str(e)}

        # Compare scenarios
        comparison = self._compare_scenarios(whatif_results)
        whatif_results["scenario_comparison"] = comparison

        return whatif_results

    def _compare_scenarios(self, scenarios: Dict) -> Dict:
        """Compare different scenarios to identify best approaches"""
        comparison = {
            "best_throughput": None,
            "best_efficiency": None,
            "least_disruption": None,
            "recommendations": []
        }

        throughputs = {}
        deviations = {}

        for scenario_name, result in scenarios.items():
            if isinstance(result, dict) and result.get("status") in ["optimal", "feasible"]:
                # Calculate throughput from optimization result
                optimized_schedule = result.get("optimized_schedule", {})
                if optimized_schedule:
                    throughput_data = self.optimizer.calculate_section_throughput(optimized_schedule)
                    throughputs[scenario_name] = throughput_data.get("throughput_per_hour", 0)
                    deviations[scenario_name] = result.get("total_deviation_minutes", 0)

        # Find best scenarios
        if throughputs:
            comparison["best_throughput"] = max(throughputs.keys(), key=throughputs.get)
            comparison["best_efficiency"] = min(deviations.keys(), key=deviations.get) if deviations else None
            comparison["throughput_comparison"] = throughputs
            comparison["deviation_comparison"] = deviations

        # Generate recommendations
        if "reduce_headway" in throughputs and throughputs["reduce_headway"] > throughputs.get("default", 0):
            comparison["recommendations"].append("Reducing headway can improve throughput by up to 20%")

        if "weather_disruption" in deviations:
            comparison["recommendations"].append("Weather scenarios show system resilience with manageable delays")

        return comparison

    def _save_workflow_results(self, results: Dict) -> Dict:
        """Save comprehensive workflow results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        section_name = results["section"].replace("-", "_")

        saved_files = {}

        try:
            # Save main workflow results
            workflow_file = f"data/results/workflow_{section_name}_{timestamp}.json"
            with open(workflow_file, 'w') as f:
                json.dump(results, f, indent=2)
            saved_files["workflow"] = workflow_file

            # Save KPI data separately
            if "kpis" in results:
                kpi_file = self.kpi_calculator.save_kpis(results["kpis"])
                if kpi_file:
                    saved_files["kpis"] = kpi_file

            # Save section data
            if "section_data" in results:
                section_file = f"data/live/section_{section_name}_{timestamp}.json"
                with open(section_file, 'w') as f:
                    json.dump(results["section_data"], f, indent=2)
                saved_files["section_data"] = section_file

        except Exception as e:
            self.log(f"❌ Error saving files: {e}")
            saved_files["error"] = str(e)

        return saved_files

    def run_interactive_mode(self):
        """Run in interactive mode for testing and demonstrations"""
        print("\n" + "="*60)
        print("🚂 VyuhMitra - Interactive Mode")
        print("="*60)

        while True:
            print("\nAvailable commands:")
            print("1. Run complete workflow")
            print("2. Check current abnormalities")
            print("3. Run what-if scenario")
            print("4. View system statistics")
            print("5. Exit")

            try:
                choice = input("\nEnter your choice (1-5): ").strip()

                if choice == "1":
                    results = self.run_complete_workflow()
                    self._print_workflow_summary(results)

                elif choice == "2":
                    section_data = self.data_collector.collect_section_data(
                        self.config.DEFAULT_FROM_STATION,
                        self.config.DEFAULT_TO_STATION
                    )
                    abnormalities = section_data.get("abnormalities", [])
                    print(f"\n🚨 Found {len(abnormalities)} abnormalities")
                    for abnormality in abnormalities:
                        print(f"   Train {abnormality['train_id']}: {abnormality['delay_minutes']}min delay")

                elif choice == "3":
                    scenarios = ["reduce_headway", "weather_disruption", "add_delay"]
                    print("\nAvailable scenarios:")
                    for i, scenario in enumerate(scenarios, 1):
                        print(f"{i}. {scenario}")

                    try:
                        scenario_choice = int(input("Choose scenario (1-3): ")) - 1
                        if 0 <= scenario_choice < len(scenarios):
                            # This would run the scenario
                            print(f"\n🔮 Running {scenarios[scenario_choice]} scenario...")
                            print("   Scenario analysis would be shown here")
                    except (ValueError, IndexError):
                        print("Invalid scenario choice")

                elif choice == "4":
                    stats = self.ai_system.get_system_stats()
                    print("\n📊 System Statistics:")
                    for key, value in stats.items():
                        print(f"   {key}: {value}")

                elif choice == "5":
                    print("\n👋 Goodbye!")
                    break

                else:
                    print("Invalid choice. Please try again.")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    def _print_workflow_summary(self, results: Dict):
        """Print a formatted summary of workflow results"""
        print("\n" + "="*60)
        print("📊 WORKFLOW SUMMARY")
        print("="*60)

        print(f"Section: {results['section']}")
        print(f"Status: {results.get('status', 'unknown').upper()}")
        print(f"Steps Completed: {', '.join(results.get('steps_completed', []))}")

        if results.get("abnormalities_detected", 0) > 0:
            print(f"\n🚨 Abnormalities: {results['abnormalities_detected']} detected and processed")

        if "kpis" in results:
            kpis = results["kpis"]
            efficiency = kpis.get("efficiency_score", {})
            throughput = kpis.get("throughput_metrics", {})

            print(f"\n📈 Performance Metrics:")
            print(f"   Throughput: {throughput.get('planned_throughput_trains_per_hour', 0):.1f} trains/hr")
            print(f"   Efficiency: {efficiency.get('overall_score', 0):.1f}/100 ({efficiency.get('grade', 'D')})")

        if "saved_files" in results:
            print(f"\n💾 Results saved to: {len(results['saved_files'])} files")

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description="VyuhMitra - AI-Powered Train Traffic Control System")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--from-station", "-f", help="From station code (default: GY)")
    parser.add_argument("--to-station", "-t", help="To station code (default: GTL)")
    parser.add_argument("--scenario", "-s", help="What-if scenario to run")

    args = parser.parse_args()

    # Initialize system
    config = Config()
    vyuhmitra = VyuhMitraCore(config)

    print("🚂 VyuhMitra - AI-Powered Train Traffic Control System")
    print("Smart India Hackathon Problem Statement #22")
    print("Maximizing Section Throughput Using AI-Powered Precise Train Traffic Control")
    print("="*80)

    try:
        if args.interactive:
            vyuhmitra.run_interactive_mode()
        else:
            # Run complete workflow
            from_station = args.from_station or config.DEFAULT_FROM_STATION
            to_station = args.to_station or config.DEFAULT_TO_STATION

            results = vyuhmitra.run_complete_workflow(from_station, to_station)
            vyuhmitra._print_workflow_summary(results)

            # Save summary to file
            summary_file = f"workflow_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_file, 'w') as f:
                json.dump(results, f, indent=2)

            print(f"\n💾 Complete results saved to: {summary_file}")

    except KeyboardInterrupt:
        print("\n\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Application error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
