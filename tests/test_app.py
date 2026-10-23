"""
NetPulse - Automated Test Suite
Covers unit tests, database operations, target validation, mocked network connectivity,
packet loss calculations, and REST API integration endpoints.
Zero external internet dependency - all network I/O is mocked.
"""

import os
import sys
import tempfile
import subprocess
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
from monitor import (
    validate_target,
    resolve_target,
    parse_ping_output,
    execute_ping,
    MonitoringManager,
)
from app import create_app


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database.init_db(db_path=path)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except PermissionError:
            pass


@pytest.fixture
def test_client(temp_db):
    """Create a Flask test client configured with the temporary database."""
    manager = MonitoringManager(db_path=temp_db)
    app = create_app({
        "TESTING": True,
        "DATABASE": temp_db,
        "MONITOR_MANAGER": manager,
    })
    with app.test_client() as client:
        yield client


# ============================================================================
# 1. Target Validation & Security Tests
# ============================================================================

class TestValidationAndSecurity:
    """Tests for validating hostnames, IPv4, IPv6, and rejecting injection."""

    def test_valid_ipv4_addresses(self):
        valid_ips = ["127.0.0.1", "8.8.8.8", "1.1.1.1", "192.168.1.100", "10.0.0.1"]
        for ip in valid_ips:
            is_valid, err = validate_target(ip)
            assert is_valid is True, f"Expected {ip} to be valid, got: {err}"
            assert err is None

    def test_valid_hostnames(self):
        valid_hosts = ["localhost", "google.com", "example.org", "dns.google", "api.github.com"]
        for host in valid_hosts:
            is_valid, err = validate_target(host)
            assert is_valid is True, f"Expected {host} to be valid, got: {err}"
            assert err is None

    def test_valid_ipv6(self):
        is_valid, err = validate_target("::1")
        assert is_valid is True
        assert err is None

    def test_reject_empty_or_whitespace(self):
        for empty_val in ["", "   ", None]:
            is_valid, err = validate_target(empty_val)
            assert is_valid is False
            assert "empty" in err.lower()

    def test_reject_command_injection_attempts(self):
        injection_payloads = [
            "localhost; rm -rf /",
            "8.8.8.8 && dir",
            "127.0.0.1 | whoami",
            "`ping 8.8.8.8`",
            "$(whoami)",
            "127.0.0.1 > file.txt",
            "localhost\ncat /etc/passwd",
            "8.8.8.8 & calc.exe",
        ]
        for payload in injection_payloads:
            is_valid, err = validate_target(payload)
            assert is_valid is False, f"Payload should have been rejected: {payload}"
            assert "invalid" in err.lower() or "character" in err.lower()

    def test_reject_excessive_length(self):
        long_host = "a" * 256 + ".com"
        is_valid, err = validate_target(long_host)
        assert is_valid is False
        assert "exceeds maximum length" in err.lower()


# ============================================================================
# 2. Network Check & Ping Logic Tests (Mocked)
# ============================================================================

class TestConnectivityChecks:
    """Mocked unit tests for network resolution and ICMP ping execution."""

    @patch("socket.gethostbyname")
    def test_dns_resolution_success(self, mock_gethostbyname):
        mock_gethostbyname.return_value = "93.184.216.34"
        ip, err = resolve_target("example.com")
        assert ip == "93.184.216.34"
        assert err is None

    @patch("socket.gethostbyname")
    def test_dns_resolution_failure(self, mock_gethostbyname):
        import socket
        mock_gethostbyname.side_effect = socket.gaierror("Name or service not known")
        ip, err = resolve_target("invalid-non-existent-domain-xyz.local")
        assert ip is None
        assert "DNS lookup failed" in err

    def test_parse_ping_output_formats(self):
        # Windows ping output format
        win_sample = "Reply from 127.0.0.1: bytes=32 time=14ms TTL=128"
        assert parse_ping_output(win_sample, "windows") == 14.0

        # Sub-millisecond format
        win_fast = "Reply from 127.0.0.1: bytes=32 time<1ms TTL=128"
        assert parse_ping_output(win_fast, "windows") == 1.0

        # Linux/macOS ping output format
        linux_sample = "64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=22.4 ms"
        assert parse_ping_output(linux_sample, "linux") == 22.4

        # No match format
        assert parse_ping_output("Request timed out.", "windows") is None

    @patch("subprocess.run")
    @patch("socket.gethostbyname")
    def test_execute_ping_reachable(self, mock_dns, mock_subproc):
        mock_dns.return_value = "127.0.0.1"
        mock_subproc.return_value = MagicMock(
            returncode=0,
            stdout="Reply from 127.0.0.1: bytes=32 time=5ms TTL=128\n",
            stderr="",
        )

        res = execute_ping("127.0.0.1", timeout_sec=2.0)
        assert res["status"] == "Reachable"
        assert res["target"] == "127.0.0.1"
        assert res["resolved_ip"] == "127.0.0.1"
        assert res["response_time_ms"] == 5.0
        assert res["error_message"] is None

    @patch("subprocess.run")
    @patch("socket.gethostbyname")
    def test_execute_ping_unreachable(self, mock_dns, mock_subproc):
        mock_dns.return_value = "192.0.2.1"
        mock_subproc.return_value = MagicMock(
            returncode=1,
            stdout="Request timed out.\n",
            stderr="",
        )

        res = execute_ping("192.0.2.1", timeout_sec=2.0)
        assert res["status"] == "Unreachable"
        assert res["response_time_ms"] is None
        assert "did not respond" in res["error_message"]

    @patch("subprocess.run")
    @patch("socket.gethostbyname")
    def test_execute_ping_timeout_exception(self, mock_dns, mock_subproc):
        mock_dns.return_value = "10.255.255.1"
        mock_subproc.side_effect = subprocess.TimeoutExpired(cmd=["ping"], timeout=2.0)

        res = execute_ping("10.255.255.1", timeout_sec=2.0)
        assert res["status"] == "Unreachable"
        assert "timed out" in res["error_message"].lower()


# ============================================================================
# 3. Database & Statistics Calculations Tests
# ============================================================================

class TestDatabaseAndMetrics:
    """Tests for SQLite persistence, CRUD, and statistical calculations."""

    def test_init_and_save_check(self, temp_db):
        check_data = {
            "target": "127.0.0.1",
            "resolved_ip": "127.0.0.1",
            "status": "Reachable",
            "response_time_ms": 12.5,
            "method": "ICMP",
            "packet_loss_pct": 0.0,
            "error_message": None,
        }
        row_id = database.save_check(check_data, db_path=temp_db)
        assert row_id > 0

        records, total = database.get_history(limit=10, db_path=temp_db)
        assert total == 1
        assert records[0]["target"] == "127.0.0.1"
        assert records[0]["response_time_ms"] == 12.5
        assert records[0]["status"] == "Reachable"

    def test_statistics_calculation_with_checks(self, temp_db):
        # Insert 3 successful checks and 1 failed check
        samples = [
            {"target": "8.8.8.8", "status": "Reachable", "response_time_ms": 20.0},
            {"target": "8.8.8.8", "status": "Reachable", "response_time_ms": 30.0},
            {"target": "8.8.8.8", "status": "Reachable", "response_time_ms": 40.0},
            {"target": "8.8.8.8", "status": "Unreachable", "response_time_ms": None},
        ]
        for s in samples:
            database.save_check(s, db_path=temp_db)

        stats = database.get_statistics(target="8.8.8.8", db_path=temp_db)
        assert stats["total_checks"] == 4
        assert stats["successful_checks"] == 3
        assert stats["failed_checks"] == 1
        # Formula: (1 / 4) * 100 = 25.0%
        assert stats["packet_loss_pct"] == 25.0
        assert stats["avg_response_time_ms"] == 30.0
        assert stats["min_response_time_ms"] == 20.0
        assert stats["max_response_time_ms"] == 40.0

    def test_statistics_empty_state_division_by_zero_safe(self, temp_db):
        stats = database.get_statistics(db_path=temp_db)
        assert stats["total_checks"] == 0
        assert stats["successful_checks"] == 0
        assert stats["failed_checks"] == 0
        assert stats["packet_loss_pct"] == 0.0
        assert stats["avg_response_time_ms"] is None

    def test_history_filtering_by_status_and_target(self, temp_db):
        database.save_check({"target": "127.0.0.1", "status": "Reachable", "response_time_ms": 1.0}, db_path=temp_db)
        database.save_check({"target": "127.0.0.1", "status": "Unreachable", "response_time_ms": None}, db_path=temp_db)
        database.save_check({"target": "8.8.8.8", "status": "Reachable", "response_time_ms": 15.0}, db_path=temp_db)

        # Filter by target
        records, total = database.get_history(target="127.0.0.1", db_path=temp_db)
        assert total == 2
        for r in records:
            assert r["target"] == "127.0.0.1"

        # Filter by status
        records, total = database.get_history(status="Unreachable", db_path=temp_db)
        assert total == 1
        assert records[0]["status"] == "Unreachable"

    def test_clear_history(self, temp_db):
        database.save_check({"target": "127.0.0.1", "status": "Reachable", "response_time_ms": 1.0}, db_path=temp_db)
        deleted = database.clear_history(db_path=temp_db)
        assert deleted == 1

        records, total = database.get_history(db_path=temp_db)
        assert total == 0


# ============================================================================
# 4. REST API Endpoint Integration Tests
# ============================================================================

class TestRestApiEndpoints:
    """Integration tests verifying JSON contract, status codes, and security."""

    def test_dashboard_index_route(self, test_client):
        res = test_client.get("/")
        assert res.status_code == 200
        assert b"NetPulse" in res.data
        assert b"Network Performance Monitor" in res.data

    def test_api_health_endpoint(self, test_client):
        res = test_client.get("/api/health")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["status"] == "online"
        assert data["database"] == "healthy"

    @patch("app.execute_ping")
    def test_api_check_valid_target(self, mock_ping, test_client):
        mock_ping.return_value = {
            "target": "127.0.0.1",
            "resolved_ip": "127.0.0.1",
            "status": "Reachable",
            "response_time_ms": 2.5,
            "method": "ICMP",
            "error_message": None,
            "details": "Echo reply received",
        }

        res = test_client.post(
            "/api/check",
            json={"target": "127.0.0.1", "save": True},
        )
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["status"] == "Reachable"
        assert json_data["data"]["response_time_ms"] == 2.5
        assert "id" in json_data["data"]

    def test_api_check_invalid_target_rejected(self, test_client):
        res = test_client.post(
            "/api/check",
            json={"target": "127.0.0.1; rm -rf /"},
        )
        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data["success"] is False
        assert "error" in json_data

    def test_api_check_empty_payload(self, test_client):
        res = test_client.post("/api/check", data="not json", content_type="text/plain")
        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data["success"] is False

    def test_api_history_and_pagination(self, test_client, temp_db):
        for i in range(5):
            database.save_check(
                {"target": f"host{i}.com", "status": "Reachable", "response_time_ms": float(10 + i)},
                db_path=temp_db,
            )

        res = test_client.get("/api/history?limit=2&offset=0")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["total"] == 5
        assert len(json_data["data"]["records"]) == 2

    def test_api_stats_endpoint(self, test_client, temp_db):
        database.save_check(
            {"target": "127.0.0.1", "status": "Reachable", "response_time_ms": 10.0},
            db_path=temp_db,
        )
        res = test_client.get("/api/stats?target=127.0.0.1")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True
        assert json_data["data"]["total_checks"] == 1
        assert json_data["data"]["avg_response_time_ms"] == 10.0

    def test_api_delete_history(self, test_client, temp_db):
        database.save_check({"target": "127.0.0.1", "status": "Reachable"}, db_path=temp_db)
        res = test_client.delete("/api/history")
        assert res.status_code == 200
        json_data = res.get_json()
        assert json_data["success"] is True
        assert json_data["deleted_count"] == 1

    def test_api_monitor_lifecycle(self, test_client):
        # 1. Start monitoring
        start_res = test_client.post(
            "/api/monitor/start",
            json={"target": "127.0.0.1", "interval": 10},
        )
        assert start_res.status_code == 200
        assert start_res.get_json()["success"] is True

        # 2. Check monitor status
        status_res = test_client.get("/api/monitor/status")
        assert status_res.status_code == 200
        status_data = status_res.get_json()["data"]
        assert status_data["is_running"] is True
        assert status_data["target"] == "127.0.0.1"

        # 3. Stop monitoring
        stop_res = test_client.post("/api/monitor/stop")
        assert stop_res.status_code == 200
        assert stop_res.get_json()["success"] is True

        # 4. Confirm stopped
        final_status = test_client.get("/api/monitor/status").get_json()["data"]
        assert final_status["is_running"] is False

    def test_api_not_found_handler(self, test_client):
        res = test_client.get("/api/non-existent-endpoint")
        assert res.status_code == 404
        assert res.get_json()["success"] is False
