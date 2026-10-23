"""
NetPulse - Flask Web Application & REST API
Provides web dashboard routing, RESTful API endpoints for network performance diagnostics,
background monitoring management, and SQLite history tracking.
"""

import logging
import os
from typing import Optional
from flask import Flask, jsonify, request, render_template

import database
from monitor import (
    validate_target,
    execute_ping,
    MonitoringManager,
    default_monitor,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("NetPulse")


def create_app(test_config: Optional[dict] = None) -> Flask:
    """
    Application factory pattern. Allows passing test configuration
    with isolated in-memory or temporary databases for automated tests.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Configuration defaults
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "netpulse-dev-secret-key-2026"),
        DATABASE=database.DEFAULT_DB_PATH,
    )

    if test_config:
        app.config.update(test_config)

    # Initialize Database schema
    db_path = app.config.get("DATABASE")
    database.init_db(db_path=db_path)

    # Attach monitor manager instance to app
    if "MONITOR_MANAGER" in app.config:
        monitor_mgr = app.config["MONITOR_MANAGER"]
    else:
        monitor_mgr = MonitoringManager(db_path=db_path)
    app.monitor_mgr = monitor_mgr

    # -------------------------------------------------------------
    # WEB DASHBOARD ROUTE
    # -------------------------------------------------------------
    @app.route("/")
    def index():
        """Render the main single-page monitoring dashboard."""
        return render_template("index.html")

    # -------------------------------------------------------------
    # REST API ENDPOINTS
    # -------------------------------------------------------------

    @app.route("/api/health", methods=["GET"])
    def api_health():
        """
        GET /api/health
        Health check endpoint confirming web server and database readiness.
        """
        try:
            # Test database connectivity
            with database.get_connection(db_path) as conn:
                conn.execute("SELECT 1").fetchone()
            db_status = "healthy"
        except Exception as e:
            logger.error("Database health check error: %s", e)
            db_status = f"unhealthy: {str(e)}"

        return (
            jsonify(
                {
                    "success": True,
                    "status": "online",
                    "application": "NetPulse Network Performance Monitor",
                    "version": "1.0.0",
                    "database": db_status,
                }
            ),
            200,
        )

    @app.route("/api/check", methods=["POST"])
    def api_check_now():
        """
        POST /api/check
        Perform an immediate one-off connectivity check for a specified target host.
        Body: {"target": "127.0.0.1", "save": true}
        """
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid JSON request body. Expected a JSON object with 'target'.",
                    }
                ),
                400,
            )

        target = data.get("target", "").strip()
        is_valid, validation_err = validate_target(target)
        if not is_valid:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": validation_err,
                    }
                ),
                400,
            )

        # Run ping check safely
        timeout_sec = 3.0
        result = execute_ping(target, timeout_sec=timeout_sec)

        # Calculate packet loss for this single probe (100% if unreachable, 0% if reachable)
        result["packet_loss_pct"] = 0.0 if result["status"] == "Reachable" else 100.0

        # Optionally persist single checks (default to true)
        should_save = data.get("save", True)
        if should_save:
            try:
                record_id = database.save_check(result, db_path=db_path)
                result["id"] = record_id
            except Exception as e:
                logger.error("Failed to save one-off check to DB: %s", e)

        return (
            jsonify(
                {
                    "success": True,
                    "data": result,
                }
            ),
            200,
        )

    @app.route("/api/history", methods=["GET"])
    def api_get_history():
        """
        GET /api/history?limit=50&offset=0&target=localhost&status=reachable
        Retrieve historical monitoring check records with optional filters.
        """
        try:
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Query parameters 'limit' and 'offset' must be valid integers.",
                    }
                ),
                400,
            )

        # Bounds checking on pagination
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        target = request.args.get("target")
        status = request.args.get("status")

        try:
            records, total_count = database.get_history(
                limit=limit,
                offset=offset,
                target=target,
                status=status,
                db_path=db_path,
            )
            return (
                jsonify(
                    {
                        "success": True,
                        "data": {
                            "records": records,
                            "total": total_count,
                            "limit": limit,
                            "offset": offset,
                        },
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("Error retrieving history: %s", e)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to retrieve monitoring history.",
                        "details": str(e),
                    }
                ),
                500,
            )

    @app.route("/api/history", methods=["DELETE"])
    def api_clear_history():
        """
        DELETE /api/history?target=example.com
        Clear check records from database (all or by target).
        """
        target = request.args.get("target")
        try:
            deleted_count = database.clear_history(target=target, db_path=db_path)
            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Successfully deleted {deleted_count} record(s).",
                        "deleted_count": deleted_count,
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("Error clearing history: %s", e)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to clear monitoring history.",
                        "details": str(e),
                    }
                ),
                500,
            )

    @app.route("/api/stats", methods=["GET"])
    def api_get_stats():
        """
        GET /api/stats?target=127.0.0.1
        Retrieve aggregate network metrics: total checks, success, fail, avg/min/max RT, packet loss.
        """
        target = request.args.get("target")
        try:
            stats = database.get_statistics(target=target, db_path=db_path)
            return (
                jsonify(
                    {
                        "success": True,
                        "data": stats,
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("Error computing statistics: %s", e)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Failed to compute performance statistics.",
                        "details": str(e),
                    }
                ),
                500,
            )

    @app.route("/api/monitor/start", methods=["POST"])
    def api_start_monitor():
        """
        POST /api/monitor/start
        Start background continuous monitoring.
        Body: {"target": "127.0.0.1", "interval": 5}
        """
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid JSON request body. Expected 'target' and optional 'interval'.",
                    }
                ),
                400,
            )

        target = data.get("target", "").strip()
        try:
            interval = int(data.get("interval", 5))
        except (ValueError, TypeError):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Interval must be an integer between 1 and 300 seconds.",
                    }
                ),
                400,
            )

        success, msg = app.monitor_mgr.start(target=target, interval=interval)
        status_code = 200 if success else 400
        return (
            jsonify(
                {
                    "success": success,
                    "message": msg,
                    "session": app.monitor_mgr.get_status(),
                }
            ),
            status_code,
        )

    @app.route("/api/monitor/stop", methods=["POST"])
    def api_stop_monitor():
        """
        POST /api/monitor/stop
        Stop any active background continuous monitoring session.
        """
        success, msg = app.monitor_mgr.stop()
        status_code = 200 if success else 400
        return (
            jsonify(
                {
                    "success": success,
                    "message": msg,
                    "session": app.monitor_mgr.get_status(),
                }
            ),
            status_code,
        )

    @app.route("/api/monitor/status", methods=["GET"])
    def api_monitor_status():
        """
        GET /api/monitor/status
        Get the current background monitoring status and session metrics.
        """
        return (
            jsonify(
                {
                    "success": True,
                    "data": app.monitor_mgr.get_status(),
                }
            ),
            200,
        )

    # -------------------------------------------------------------
    # ERROR HANDLERS
    # -------------------------------------------------------------
    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "API route not found."}), 404
        return render_template("index.html"), 404

    @app.errorhandler(500)
    def handle_server_error(e):
        logger.error("Unhandled internal server error: %s", e)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "An internal server error occurred.",
                }
            ),
            500,
        )

    return app


# Create the default instance for WSGI servers and running directly
app = create_app()


if __name__ == "__main__":
    # Host on 127.0.0.1 and port 5000 for standard local development
    port = int(os.environ.get("PORT", 5000))
    print(f"\n==================================================")
    print(f" NetPulse Network Performance Monitoring System")
    print(f" Dashboard: http://127.0.0.1:{port}/")
    print(f" Health check: http://127.0.0.1:{port}/api/health")
    print(f"==================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
