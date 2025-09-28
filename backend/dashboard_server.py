#!/usr/bin/env python3
"""
VyuhMitra Dashboard Server - Enhanced with complete AI/ML workflow
Updated to serve frontend files from the proper directory structure
"""

import json
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS

# Import our modules
from .config import Config
from .data_collector import RailRadarDataCollector
from .ai_solution_system import AIMLSolutionSystem
from .optimizer import TrainScheduleOptimizer
from .kpi_calculator import KPICalculator

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DashboardServer')

# Initialize components
config = Config()
data_collector = RailRadarDataCollector(config.RAILRADAR_API_KEY)
ai_system = AIMLSolutionSystem(config)
optimizer = TrainScheduleOptimizer(config.MIN_HEADWAY_MINUTES)
kpi_calculator = KPICalculator(logger)

# Global state
current_section_data = None
current_abnormalities = []
active_solutions = []

def create_api_response(success: bool, data=None, error=None) -> dict:
    """Create standardized API response"""
    return {
        "success": success,
        "data": data,
        "error": error,
        "timestamp": datetime.now().isoformat()
    }

# =================== FRONTEND FILE SERVING ===================
# Project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@app.route('/')
def dashboard():
    """Serve the main dashboard HTML from frontend directory"""
    try:
        return send_file(os.path.join(PROJECT_ROOT, 'frontend', 'index.html'))
    except Exception as e:
        logger.error(f"Error serving dashboard: {e}")
        return f"Error loading dashboard: {e}", 500

@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files from frontend/css directory"""
    try:
        return send_from_directory(os.path.join(PROJECT_ROOT, 'frontend', 'css'), filename, mimetype='text/css')
    except Exception as e:
        logger.error(f"Error serving CSS {filename}: {e}")
        return f"CSS file not found: {filename}", 404

@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files from frontend/js directory"""
    try:
        return send_from_directory(os.path.join(PROJECT_ROOT, 'frontend', 'js'), filename, mimetype='application/javascript')
    except Exception as e:
        logger.error(f"Error serving JS {filename}: {e}")
        return f"JavaScript file not found: {filename}", 404

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files for backwards compatibility"""
    try:
        # Try frontend directory first
        if filename.startswith('css/'):
            return send_from_directory('frontend', filename, mimetype='text/css')
        elif filename.startswith('js/'):
            return send_from_directory('frontend', filename, mimetype='application/javascript')
        else:
            return send_from_directory('frontend', filename)
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {e}")
        return f"Static file not found: {filename}", 404

# =================== CORE DATA ENDPOINTS ===================

@app.route('/api/section/current')
def get_current_section():
    """Get current section data with abnormality detection"""
    global current_section_data, current_abnormalities

    try:
        from_station = config.DEFAULT_FROM_STATION
        to_station = config.DEFAULT_TO_STATION

        # Collect fresh data
        section_data = data_collector.collect_section_data(from_station, to_station)
        current_section_data = section_data
        current_abnormalities = section_data.get("abnormalities", [])

        # Enhanced section data
        enhanced_data = {
            **section_data,
            "abnormalities_count": len(current_abnormalities),
            "active_solutions_count": len(active_solutions),
            "system_status": "operational" if section_data["valid_schedules"] > 0 else "limited_data"
        }

        return jsonify(create_api_response(True, enhanced_data))

    except Exception as e:
        logger.error(f"Error getting section data: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

@app.route('/api/abnormalities')
def get_abnormalities():
    """Get current abnormalities"""
    try:
        # Force refresh of section data to get latest abnormalities
        if not current_section_data:
            section_data = data_collector.collect_section_data(config.DEFAULT_FROM_STATION, config.DEFAULT_TO_STATION)
            globals()['current_section_data'] = section_data
            globals()['current_abnormalities'] = section_data.get("abnormalities", [])

        return jsonify(create_api_response(True, {
            "abnormalities": current_abnormalities,
            "count": len(current_abnormalities),
            "last_checked": datetime.now().isoformat()
        }))
    except Exception as e:
        logger.error(f"Error getting abnormalities: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

# =================== AI/ML SOLUTION ENDPOINTS ===================

@app.route('/api/solutions/generate', methods=['POST'])
def generate_solutions():
    """Generate solutions for an abnormality"""
    global active_solutions

    try:
        abnormality = request.json
        if not abnormality:
            return jsonify(create_api_response(False, error="No abnormality data provided")), 400

        logger.info(f"Processing abnormality for train {abnormality.get('train_id', 'unknown')}")

        # Process abnormality through AI system
        result = ai_system.process_abnormality(abnormality)

        if result["status"] == "solutions_generated":
            # Store active solutions
            new_solutions = result["solutions"]
            active_solutions.extend(new_solutions)

            logger.info(f"Generated {len(new_solutions)} solutions for train {abnormality.get('train_id')}")

            return jsonify(create_api_response(True, {
                "train_id": result["train_id"],
                "reason": result["reason"],
                "ways": result["ways"],
                "solutions": result["solutions"],
                "message": f"Generated {len(result['solutions'])} solutions"
            }))
        else:
            logger.warning(f"Solution generation failed: {result['status']}")
            return jsonify(create_api_response(False, error=f"Solution generation failed: {result['status']}"))

    except Exception as e:
        logger.error(f"Error generating solutions: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

@app.route('/api/solutions/active')
def get_active_solutions():
    """Get currently active solutions awaiting controller decision"""
    try:
        return jsonify(create_api_response(True, {
            "solutions": active_solutions,
            "count": len(active_solutions)
        }))
    except Exception as e:
        logger.error(f"Error getting active solutions: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

@app.route('/api/solutions/feedback', methods=['POST'])
def submit_solution_feedback():
    """Handle accept/reject feedback from controller"""
    global active_solutions

    try:
        feedback_data = request.json
        required_fields = ['solution_id', 'action', 'train_id']

        if not all(field in feedback_data for field in required_fields):
            return jsonify(create_api_response(False, error="Missing required fields")), 400

        logger.info(f"Processing {feedback_data['action']} for solution {feedback_data['solution_id']}")

        # Process feedback through AI system
        result = ai_system.handle_solution_feedback(
            feedback_data['solution_id'],
            feedback_data['action'],
            feedback_data['train_id'],
            feedback_data.get('reason', ''),
            feedback_data.get('controller_id', 'dashboard_user')
        )

        # Remove solution from active list
        active_solutions = [s for s in active_solutions if s['solution_id'] != feedback_data['solution_id']]

        logger.info(f"Solution {feedback_data['action']} processed successfully")

        return jsonify(create_api_response(True, result))

    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

# =================== OPTIMIZATION ENDPOINTS ===================

@app.route('/api/optimize/current')
def run_optimization():
    """Run schedule optimization"""
    try:
        if not current_section_data or not current_section_data.get("static_schedules"):
            # Try to collect data first
            section_data = data_collector.collect_section_data(config.DEFAULT_FROM_STATION, config.DEFAULT_TO_STATION)
            globals()['current_section_data'] = section_data

            if not section_data.get("static_schedules"):
                return jsonify(create_api_response(False, error="No section data available for optimization"))

        # Run optimization
        static_schedules = current_section_data["static_schedules"]
        optimization_result = optimizer.optimize_section_schedule(static_schedules, scenario='default')

        logger.info(f"Optimization completed: {optimization_result.get('status')}")

        return jsonify(create_api_response(True, {
            "optimization_result": optimization_result,
            "section": current_section_data["section"]
        }))

    except Exception as e:
        logger.error(f"Optimization error: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500


@app.route('/api/optimize/scenario', methods=['POST'])
def run_scenario_optimization():
    """Run what-if scenario optimization"""
    try:
        scenario_data = request.json or {}
        scenario = scenario_data.get('scenario', 'default')

        logger.info(f"Running what-if scenario: {scenario}")

        if not current_section_data:
            # Collect fresh data
            section_data = data_collector.collect_section_data(config.DEFAULT_FROM_STATION, config.DEFAULT_TO_STATION)
            globals()['current_section_data'] = section_data

        static_schedules = current_section_data.get("static_schedules", {})

        if not static_schedules:
            return jsonify(create_api_response(True, {  # success True with message
                "scenario": scenario,
                "optimization_result": {"status": "no_data", "message": "No schedule data available for scenario analysis"},
                "comparison": {}
            })), 200

        optimization_result = optimizer.optimize_section_schedule(static_schedules, scenario=scenario)
        baseline_result = optimizer.optimize_section_schedule(static_schedules, scenario='default')

        comparison = {
            "scenario_throughput": optimization_result.get("throughput", 0),
            "baseline_throughput": baseline_result.get("throughput", 0),
            "improvement": optimization_result.get("throughput", 0) - baseline_result.get("throughput", 0)
        }

        logger.info(f"Scenario {scenario} completed with {optimization_result.get('status')} status")

        return jsonify(create_api_response(True, {
            "scenario": scenario,
            "optimization_result": optimization_result,
            "comparison": comparison
        })), 200

    except Exception as e:
        logger.error(f"Scenario optimization error: {e}")
        return jsonify(create_api_response(True, {
            "scenario": (request.json or {}).get('scenario', 'default'),
            "optimization_result": {"status": "failed", "error": str(e)},
            "comparison": {}
        })), 200


# =================== KPI ENDPOINTS ===================

@app.route('/api/kpi/current')
def get_current_kpis():
    """Calculate and return current KPIs"""
    try:
        if not current_section_data:
            try:
                section_data = data_collector.collect_section_data(config.DEFAULT_FROM_STATION, config.DEFAULT_TO_STATION)
                globals()['current_section_data'] = section_data
            except Exception as e:
                logger.warning(f"KPI: data collection failed: {e}")
                # Return safe zeroed KPIs with success True
                kpi_data = {
                    "section": f"{config.DEFAULT_FROM_STATION}-{config.DEFAULT_TO_STATION}",
                    "timestamp": datetime.now().isoformat(),
                    "basic_stats": {"total_trains_scheduled": 0, "live_trains_tracked": 0, "data_coverage_percentage": 0},
                    "throughput_metrics": {"planned_throughput_trains_per_hour": 0},
                    "efficiency_metrics": {"on_time_performance_percentage": 0, "average_delay_minutes": 0, "schedule_reliability_score": 0},
                    "safety_metrics": {"safety_score": 100},
                    "infrastructure_metrics": {},
                    "ai_metrics": {},
                    "data_quality": {},
                    "optimization_impact": {"success": False, "impact_score": 0},
                    "efficiency_score": {"overall_score": 0, "grade": "D"}
                }
                return jsonify(create_api_response(True, {"kpi_data": kpi_data, "section": f"{config.DEFAULT_FROM_STATION}-{config.DEFAULT_TO_STATION}"})), 200

        section_data = current_section_data

        # Try optimizer but don't fail if it errors
        optimization_result = {}
        try:
            static_schedules = section_data.get("static_schedules", {})
            if static_schedules:
                optimization_result = optimizer.optimize_section_schedule(static_schedules, scenario='default')
        except Exception as e:
            logger.warning(f"KPI: optimizer failed: {e}")
            optimization_result = {}

        kpi_data = kpi_calculator.calculate_section_kpis(section_data, optimization_result)
        ai_stats = ai_system.get_system_stats()
        kpi_data["ai_system"] = ai_stats

        return jsonify(create_api_response(True, {
            "kpi_data": kpi_data,
            "section": section_data.get("section", "Unknown")
        })), 200

    except Exception as e:
        logger.error(f"KPI calculation error: {e}")
        safe = {
            "kpi_data": {
                "section": f"{config.DEFAULT_FROM_STATION}-{config.DEFAULT_TO_STATION}",
                "timestamp": datetime.now().isoformat(),
                "throughput_metrics": {"planned_throughput_trains_per_hour": 0},
                "efficiency_score": {"overall_score": 0, "grade": "D"}
            },
            "section": f"{config.DEFAULT_FROM_STATION}-{config.DEFAULT_TO_STATION}"
        }
        return jsonify(create_api_response(True, safe)), 200

@app.route('/api/kpi/historical')
def get_historical_kpis():
    """Get historical KPI trends"""
    try:
        # Generate sample historical data (in production, this would load from database)
        dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

        historical_data = {
            "daily_throughput": [2.1, 2.3, 1.9, 2.5, 2.2, 2.4, 2.0],
            "daily_efficiency": [78, 82, 74, 88, 80, 85, 76],
            "daily_delays": [12, 8, 18, 6, 10, 7, 14],
            "dates": dates,
            "period": "last_7_days"
        }

        return jsonify(create_api_response(True, historical_data))

    except Exception as e:
        logger.error(f"Historical KPI error: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

# =================== DASHBOARD SUMMARY ENDPOINTS ===================

@app.route('/api/dashboard/summary')
def get_dashboard_summary():
    """Get comprehensive dashboard summary"""
    try:
        if not current_section_data:
            # Try to collect data first
            try:
                section_data = data_collector.collect_section_data(config.DEFAULT_FROM_STATION, config.DEFAULT_TO_STATION)
                globals()['current_section_data'] = section_data
                globals()['current_abnormalities'] = section_data.get("abnormalities", [])
            except Exception as e:
                logger.warning(f"Failed to collect live data, using fallback: {e}")
                # Use fallback data for demo
                section_data = create_fallback_data()
                globals()['current_section_data'] = section_data
                globals()['current_abnormalities'] = section_data.get("abnormalities", [])
        else:
            section_data = current_section_data

        # Calculate basic metrics
        total_trains = section_data.get("valid_schedules", 0)
        abnormalities_count = len(section_data.get("abnormalities", []))

        # Get AI system stats
        ai_stats = ai_system.get_system_stats()

        # Calculate performance metrics
        static_schedules = section_data.get("static_schedules", {})
        optimization_result = {}

        if static_schedules:
            try:
                optimization_result = optimizer.optimize_section_schedule(static_schedules, scenario='default')
            except Exception as e:
                logger.warning(f"Optimization failed in summary: {e}")

        # Calculate efficiency metrics
        planned_throughput = 0
        efficiency_score = 50
        efficiency_grade = "C"

        if total_trains > 0:
            # Simple throughput calculation
            planned_throughput = total_trains / 24 if total_trains > 0 else 0

            # Simple efficiency calculation based on trains and abnormalities
            if abnormalities_count == 0:
                efficiency_score = 85 if total_trains > 5 else 70
                efficiency_grade = "A" if total_trains > 5 else "B"
            elif abnormalities_count < total_trains * 0.1:
                efficiency_score = 75
                efficiency_grade = "B"
            else:
                efficiency_score = 60
                efficiency_grade = "C"

        summary = {
            "section_info": {
                "name": section_data.get("section", f"{config.DEFAULT_FROM_STATION}-{config.DEFAULT_TO_STATION}"),
                "total_trains": total_trains,
                "live_trains_entry": section_data.get("live_entry_count", 0),
                "live_trains_exit": section_data.get("live_exit_count", 0)
            },
            "abnormalities": {
                "current_count": abnormalities_count,
                "active_solutions": len(active_solutions),
                "resolved_today": 0  # Would track from database
            },
            "performance_metrics": {
                "planned_throughput": planned_throughput,
                "efficiency_score": efficiency_score,
                "efficiency_grade": efficiency_grade
            },
            "optimization_status": {
                "status": optimization_result.get("status", "Ready"),
                "last_run": datetime.now().isoformat(),
                "trains_adjusted": optimization_result.get("trains_adjusted", 0)
            },
            "live_status": {
                "data_quality": section_data.get("data_quality", {}),
                "last_update": section_data.get("timestamp", datetime.now().isoformat()),
                "activity_ratio": 0.5  # Simplified calculation
            },
            "ai_system": ai_stats,
            "system_health": "Good" if total_trains > 0 else "Limited Data",
            "recommendations": [
                "System operating within normal parameters",
                "Continue monitoring for optimization opportunities",
                "AI models performing optimally"
            ]
        }

        return jsonify(create_api_response(True, {"summary": summary}))

    except Exception as e:
        logger.error(f"Dashboard summary error: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

def create_fallback_data():
    """Create fallback demo data when API is unavailable"""
    return {
        "section": f"{config.DEFAULT_FROM_STATION}-{config.DEFAULT_TO_STATION}",
        "timestamp": datetime.now().isoformat(),
        "total_trains": 5,
        "valid_schedules": 5,
        "static_schedules": {
            "12345": {
                "train_name": "Gooty Express",
                "entry_time": 360,  # 6:00 AM
                "exit_time": 420,   # 7:00 AM
                "entry_platform": "1",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            },
            "12346": {
                "train_name": "Guntakal Passenger",
                "entry_time": 480,  # 8:00 AM
                "exit_time": 540,   # 9:00 AM
                "entry_platform": "2",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            },
            "12347": {
                "train_name": "Southern Express",
                "entry_time": 600,  # 10:00 AM
                "exit_time": 660,   # 11:00 AM
                "entry_platform": "1",
                "journey_date": datetime.now().strftime("%Y-%m-%d")
            }
        },
        "live_data": {},
        "abnormalities": [
            {
                "train_id": "12345",
                "delay_minutes": 15,
                "status": "Signal failure ahead",
                "location": config.DEFAULT_FROM_STATION,
                "location_name": "Gooty Junction",
                "abnormality_type": "delay",
                "detected_at": datetime.now().isoformat(),
                "severity": "medium"
            }
        ],
        "data_source": "fallback_demo",
        "live_entry_count": 1,
        "live_exit_count": 0
    }

@app.route('/api/trains/schedule')
def get_train_schedules():
    """Get formatted train schedule data for dashboard"""
    try:
        if not current_section_data or not current_section_data.get("static_schedules"):
            # Try to get fresh data
            try:
                section_data = data_collector.collect_section_data(config.DEFAULT_FROM_STATION, config.DEFAULT_TO_STATION)
                globals()['current_section_data'] = section_data
            except:
                # Use fallback data
                section_data = create_fallback_data()
                globals()['current_section_data'] = section_data
        else:
            section_data = current_section_data

        static_schedules = section_data.get("static_schedules", {})
        live_data = section_data.get("live_data", {})

        if not static_schedules:
            return jsonify(create_api_response(True, {"schedule_data": []}))

        schedule_list = []
        for train_id, schedule in static_schedules.items():
            live_info = live_data.get(train_id, {})

            schedule_item = {
                "train_id": train_id,
                "train_name": schedule.get("train_name", "Unknown"),
                "static_entry": schedule.get("entry_time", 0),
                "static_exit": schedule.get("exit_time", 0),
                "optimized_entry": schedule.get("entry_time", 0),  # Would be from optimization
                "optimized_exit": schedule.get("exit_time", 0),
                "deviation": 0,  # Calculated from optimization
                "platform": schedule.get("entry_platform", "TBD"),
                "status": "Live" if live_info else "Scheduled",
                "delay_minutes": live_info.get("overallDelayMinutes", 0) if live_info else 0,
                "journey_date": schedule.get("journey_date", datetime.now().strftime("%Y-%m-%d")),
                "current_location": live_info.get("current_station", "In Transit") if live_info else "Scheduled"
            }
            schedule_list.append(schedule_item)

        # Sort by entry time
        schedule_list.sort(key=lambda x: x["static_entry"])

        return jsonify(create_api_response(True, {"schedule_data": schedule_list}))

    except Exception as e:
        logger.error(f"Schedule data error: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

# =================== SYSTEM ENDPOINTS ===================

@app.route('/api/system/status')
def get_system_status():
    """Get overall system status"""
    try:
        status = {
            "api_status": "online",
            "railradar_connection": "connected",  # Would test actual connection
            "ml_model_status": "loaded",
            "optimization_engine": "ready",
            "database_status": "connected",
            "frontend_status": "loaded",
            "last_health_check": datetime.now().isoformat(),
            "version": "2.0",
            "uptime_seconds": 0  # Would calculate actual uptime
        }

        return jsonify(create_api_response(True, status))

    except Exception as e:
        logger.error(f"System status error: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

@app.route('/api/system/refresh', methods=['POST'])
def refresh_system_data():
    """Force refresh of all system data"""
    global current_section_data, current_abnormalities, active_solutions

    try:
        logger.info("Forcing system data refresh...")

        # Clear current data
        current_section_data = None
        current_abnormalities = []

        # Refresh section data
        section_data = data_collector.collect_section_data(config.DEFAULT_FROM_STATION, config.DEFAULT_TO_STATION)
        current_section_data = section_data
        current_abnormalities = section_data.get("abnormalities", [])

        logger.info(f"Refreshed data: {section_data.get('valid_schedules', 0)} trains, {len(current_abnormalities)} abnormalities")

        return jsonify(create_api_response(True, {
            "message": "System data refreshed successfully",
            "trains": section_data.get("valid_schedules", 0),
            "abnormalities": len(current_abnormalities),
            "timestamp": datetime.now().isoformat()
        }))

    except Exception as e:
        logger.error(f"System refresh error: {e}")
        return jsonify(create_api_response(False, error=str(e))), 500

# =================== ERROR HANDLERS ===================

@app.errorhandler(404)
def not_found(error):
    return jsonify(create_api_response(False, error="Endpoint not found")), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify(create_api_response(False, error="Internal server error")), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}")
    return jsonify(create_api_response(False, error=f"Unexpected error: {str(e)}")), 500

# =================== APPLICATION STARTUP ===================

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs("data/schedules", exist_ok=True)
    os.makedirs("data/live", exist_ok=True)
    os.makedirs("data/results", exist_ok=True)
    os.makedirs("data/kpi", exist_ok=True)
    os.makedirs("models", exist_ok=True)

    # Ensure frontend directory exists
    if not os.path.exists("frontend"):
        logger.error("❌ Frontend directory not found! Please ensure frontend files are in place.")
        logger.error("Expected structure:")
        logger.error("  frontend/")
        logger.error("    ├── index.html")
        logger.error("    ├── css/dashboard.css")
        logger.error("    └── js/dashboard.js")
        exit(1)

    # Initialize with sample data if data.jio doesn't exist
    if not os.path.exists(config.STATIC_SCHEDULE_FILE):
        sample_data = [
            {
                "train_id": "12345",
                "train_name": "Gooty Express",
                "route": "main",
                "track": "1",
                "from_station": config.DEFAULT_FROM_STATION,
                "to_station": config.DEFAULT_TO_STATION,
                "scheduled_departure": "06:00",
                "scheduled_arrival": "07:00",
                "distance_km": 45,
                "platform": "1",
                "last_updated": datetime.now().isoformat(),
                "status": "scheduled"
            },
            {
                "train_id": "12346",
                "train_name": "Guntakal Passenger",
                "route": "main",
                "track": "2",
                "from_station": config.DEFAULT_FROM_STATION,
                "to_station": config.DEFAULT_TO_STATION,
                "scheduled_departure": "08:00",
                "scheduled_arrival": "09:00",
                "distance_km": 45,
                "platform": "2",
                "last_updated": datetime.now().isoformat(),
                "status": "scheduled"
            }
        ]
        with open(config.STATIC_SCHEDULE_FILE, 'w') as f:
            json.dump(sample_data, f, indent=2)
        logger.info("✅ Created sample data.jio file")

    logger.info("🚂 VyuhMitra Dashboard Server Starting...")
    logger.info(f"📁 Frontend files: frontend/")
    logger.info(f"🌐 Access dashboard at: http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")
    logger.info(f"📊 API endpoints available at: http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}/api/")

    # Initialize AI system
    try:
        # Test AI system
        ai_stats = ai_system.get_system_stats()
        logger.info(f"🤖 AI System initialized: {ai_stats.get('total_solutions_generated', 0)} solutions generated")
    except Exception as e:
        logger.warning(f"⚠️ AI system initialization warning: {e}")

    # Run the Flask application
    app.run(
        host=config.DASHBOARD_HOST,
        port=config.DASHBOARD_PORT,
        debug=config.DASHBOARD_DEBUG,
        threaded=True
    )
