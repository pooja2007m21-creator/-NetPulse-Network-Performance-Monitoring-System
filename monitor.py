"""
NetPulse - Network Monitoring Engine
Handles target validation, platform-aware ICMP ping execution, response time measurement,
packet loss computation, and background thread monitoring management.
"""

import ipaddress
import os
import platform
import re
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

import database

# Hostname validation regex according to RFC 1123
HOSTNAME_REGEX = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
    r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
)

# Forbidden characters that could be abused or indicate shell injection attempts
FORBIDDEN_CHARS = set(";&|`$><(){}[]*?~^!%\"'\\ \t\r\n")


def validate_target(target: str) -> Tuple[bool, Optional[str]]:
    """
    Validate target host input.
    Accepts valid IPv4, IPv6, or standard hostnames (e.g. 'localhost', '127.0.0.1', 'google.com').
    Rejects empty inputs, shell metacharacters, spaces, and invalid formatting.

    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    if not target or not isinstance(target, str):
        return False, "Target host cannot be empty."

    target = target.strip()
    if not target:
        return False, "Target host cannot be empty."

    if len(target) > 255:
        return False, "Target host exceeds maximum length of 255 characters."

    # Check for forbidden characters
    if any(c in FORBIDDEN_CHARS for c in target):
        return False, "Invalid characters detected. Only valid hostnames or IP addresses are permitted."

    # Check if target is a valid IP address (IPv4 or IPv6)
    try:
        ipaddress.ip_address(target)
        return True, None
    except ValueError:
        pass

    # Check if target is a valid RFC-compliant hostname / domain name
    if HOSTNAME_REGEX.match(target):
        return True, None

    return False, "Invalid hostname or IP address format. Example: 'localhost', '8.8.8.8', or 'example.com'."


def resolve_target(target: str, timeout: float = 2.0) -> Tuple[Optional[str], Optional[str]]:
    """
    Safely resolve a hostname to an IP address with a socket timeout.
    Returns (resolved_ip, error_message).
    """
    # If already an IP address, return immediately
    try:
        ipaddress.ip_address(target)
        return target, None
    except ValueError:
        pass

    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        resolved_ip = socket.gethostbyname(target)
        return resolved_ip, None
    except socket.gaierror as e:
        return None, f"DNS lookup failed: Unable to resolve hostname '{target}'."
    except socket.timeout:
        return None, f"DNS lookup timed out for '{target}' after {timeout} seconds."
    except Exception as e:
        return None, f"DNS resolution error: {str(e)}"
    finally:
        socket.setdefaulttimeout(old_timeout)


def parse_ping_output(output: str, system: str) -> Optional[float]:
    """
    Extract round-trip time in milliseconds from ping command output if available.
    """
    if not output:
        return None

    # Matches "time=14.2 ms", "time=14ms", "time<1ms", "time 14ms"
    match = re.search(r"time[<=]?\s*([0-9.]+)\s*ms", output, re.IGNORECASE)
    if match:
        try:
            return round(float(match.group(1)), 2)
        except (ValueError, TypeError):
            pass

    return None


def execute_ping(target: str, timeout_sec: float = 2.0) -> Dict[str, Any]:
    """
    Execute a platform-aware ICMP ping safely using subprocess with a list of arguments (never shell=True).
    Measures duration with high-precision monotonic clock.

    Returns a comprehensive result dictionary with:
        - target
        - resolved_ip
        - status: 'Reachable', 'Unreachable', or 'Unknown'
        - response_time_ms: float or None
        - method: 'ICMP'
        - error_message: str or None
        - details: str
    """
    is_valid, validation_err = validate_target(target)
    if not is_valid:
        return {
            "target": target,
            "resolved_ip": None,
            "status": "Unknown",
            "response_time_ms": None,
            "method": "ICMP",
            "error_message": validation_err,
            "details": "Target validation rejected the input.",
        }

    resolved_ip, dns_err = resolve_target(target, timeout=timeout_sec)
    if not resolved_ip and dns_err:
        return {
            "target": target,
            "resolved_ip": None,
            "status": "Unreachable",
            "response_time_ms": None,
            "method": "ICMP",
            "error_message": dns_err,
            "details": "Host could not be reached because DNS resolution failed.",
        }

    current_os = platform.system().lower()
    timeout_ms = int(timeout_sec * 1000)

    # Build safe argument list based on OS
    if current_os == "windows":
        # -n 1: 1 echo request; -w <ms>: timeout in milliseconds
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), target]
    elif current_os == "darwin":  # macOS
        # -c 1: 1 echo request; -W <ms>: timeout in ms on newer macOS or -t <sec>
        cmd = ["ping", "-c", "1", "-W", str(timeout_ms), target]
    else:  # Linux and other UNIX
        # -c 1: 1 echo request; -W <sec>: timeout in seconds
        cmd = ["ping", "-c", "1", "-W", str(max(1, int(round(timeout_sec)))), target]

    start_time = time.perf_counter()
    try:
        # Run subprocess with list of arguments, shell=False to prevent command injection
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec + 1.0,  # Buffer to allow child process timeout to trigger
            shell=False,
        )
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        combined_output = stdout + "\n" + stderr

        # Check for unreachable indicators in output
        unreachable_indicators = [
            "destination host unreachable",
            "request timed out",
            "100% packet loss",
            "100% loss",
            "unknown host",
            "could not find host",
            "transmit failed",
            "general failure",
        ]

        output_lower = combined_output.lower()
        has_unreachable_pattern = any(ind in output_lower for ind in unreachable_indicators)

        if proc.returncode == 0 and not has_unreachable_pattern:
            parsed_rt = parse_ping_output(stdout, current_os)
            # Use parsed round-trip time if available; fallback to high-resolution measured timer
            final_rt = parsed_rt if parsed_rt is not None else elapsed_ms
            return {
                "target": target,
                "resolved_ip": resolved_ip,
                "status": "Reachable",
                "response_time_ms": final_rt,
                "method": "ICMP",
                "error_message": None,
                "details": f"Host responded in {final_rt} ms. ICMP Echo Reply received.",
            }
        else:
            return {
                "target": target,
                "resolved_ip": resolved_ip,
                "status": "Unreachable",
                "response_time_ms": None,
                "method": "ICMP",
                "error_message": "Host did not respond to ICMP Echo Request.",
                "details": (
                    "No response within timeout. Note: The host may be offline, "
                    "or ICMP echo requests may be blocked by a local/remote firewall."
                ),
            }

    except subprocess.TimeoutExpired:
        return {
            "target": target,
            "resolved_ip": resolved_ip,
            "status": "Unreachable",
            "response_time_ms": None,
            "method": "ICMP",
            "error_message": f"Ping operation timed out after {timeout_sec} seconds.",
            "details": "Process exceeded maximum execution timeout limit.",
        }
    except FileNotFoundError:
        return {
            "target": target,
            "resolved_ip": resolved_ip,
            "status": "Unknown",
            "response_time_ms": None,
            "method": "ICMP",
            "error_message": "System ping utility not found in PATH.",
            "details": "Unable to invoke system ping command.",
        }
    except PermissionError:
        return {
            "target": target,
            "resolved_ip": resolved_ip,
            "status": "Unknown",
            "response_time_ms": None,
            "method": "ICMP",
            "error_message": "Insufficient permissions to execute ICMP ping.",
            "details": "OS permission denied when opening raw network socket or ping utility.",
        }
    except Exception as e:
        return {
            "target": target,
            "resolved_ip": resolved_ip,
            "status": "Unknown",
            "response_time_ms": None,
            "method": "ICMP",
            "error_message": f"Unexpected error during connectivity check: {str(e)}",
            "details": "An unhandled exception occurred in the monitoring worker.",
        }


class MonitoringManager:
    """
    Manages continuous background monitoring using a dedicated daemon thread.
    Thread-safe, handles start/stop lifecycle cleanly, and records checks in SQLite.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Active session state
        self.target: Optional[str] = None
        self.interval: int = 5
        self.is_running: bool = False
        self.started_at: Optional[str] = None
        self.total_checks: int = 0
        self.successful_checks: int = 0
        self.failed_checks: int = 0
        self.last_check: Optional[Dict[str, Any]] = None

    def start(self, target: str, interval: int = 5) -> Tuple[bool, str]:
        """
        Start continuous background monitoring for a target.
        """
        with self._lock:
            if self.is_running:
                return False, f"Monitoring is already running for '{self.target}'. Stop it before starting a new session."

            is_valid, err = validate_target(target)
            if not is_valid:
                return False, err or "Invalid target."

            if not (1 <= interval <= 300):
                return False, "Interval must be between 1 and 300 seconds."

            self.target = target.strip()
            self.interval = interval
            self.total_checks = 0
            self.successful_checks = 0
            self.failed_checks = 0
            self.last_check = None
            self.started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            self._stop_event.clear()
            self.is_running = True

            self._thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name=f"NetPulseMonitor-{self.target}",
            )
            self._thread.start()
            return True, f"Monitoring started for '{self.target}' every {self.interval}s."

    def stop(self) -> Tuple[bool, str]:
        """
        Signal the background monitoring thread to stop and wait for it.
        """
        with self._lock:
            if not self.is_running:
                return False, "No active monitoring session is currently running."

            self._stop_event.set()
            self.is_running = False
            msg = f"Monitoring stopped for '{self.target}'."

        # Wait briefly for thread to finish outside lock
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

        return True, msg

    def get_status(self) -> Dict[str, Any]:
        """
        Return the current state and metrics of the monitoring manager.
        """
        with self._lock:
            packet_loss = (
                round((self.failed_checks / self.total_checks) * 100, 2)
                if self.total_checks > 0
                else 0.0
            )
            return {
                "is_running": self.is_running,
                "target": self.target,
                "interval": self.interval,
                "started_at": self.started_at,
                "total_checks": self.total_checks,
                "successful_checks": self.successful_checks,
                "failed_checks": self.failed_checks,
                "packet_loss_pct": packet_loss,
                "last_check": self.last_check,
            }

    def _worker_loop(self) -> None:
        """
        Continuous loop run in the daemon thread.
        Performs ping check, saves to database, updates session stats,
        and waits for the configured interval or stop event.
        """
        while not self._stop_event.is_set():
            current_target = self.target
            if not current_target:
                break

            result = execute_ping(current_target, timeout_sec=min(3.0, float(self.interval)))

            with self._lock:
                self.total_checks += 1
                if result.get("status") == "Reachable":
                    self.successful_checks += 1
                else:
                    self.failed_checks += 1

                # Calculate cumulative session packet loss
                session_loss = round((self.failed_checks / self.total_checks) * 100, 2)
                result["packet_loss_pct"] = session_loss
                result["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                self.last_check = result

            # Persist to database
            try:
                database.save_check(result, db_path=self.db_path)
            except Exception as e:
                # Log error without crashing thread
                print(f"[NetPulse Worker Error] Failed to persist check: {e}")

            # Sleep for interval or wake up early if stop event was signalled
            if self._stop_event.wait(timeout=self.interval):
                break


# Default singleton instance for the application
default_monitor = MonitoringManager()
