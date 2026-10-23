"""
NetPulse - Database Module
Handles SQLite initialization, connection lifecycle, and CRUD operations for network monitoring history and statistics.
Designed with thread safety, parameterization to prevent SQL injection, and custom db_path support for testing.
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Default database file path inside the project's data directory
DEFAULT_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "netpulse.db")


def get_db_path(custom_path: Optional[str] = None) -> str:
    """Return the active database path, ensuring parent directory exists."""
    db_path = custom_path or DEFAULT_DB_PATH
    if db_path != ":memory:":
        parent_dir = os.path.dirname(db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
    return db_path


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Open and return a new SQLite connection configured with Row factory
    for easy dictionary-like access.
    """
    path = get_db_path(db_path)
    conn = sqlite3.connect(path, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable Write-Ahead Logging (WAL) for better concurrent read/write performance
    if path != ":memory:":
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
        except sqlite3.DatabaseError:
            pass
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initialize SQLite schema: creates the `checks` table and indexes.
    Safe to call multiple times (IF NOT EXISTS).
    """
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                resolved_ip TEXT,
                status TEXT NOT NULL,
                response_time_ms REAL,
                method TEXT DEFAULT 'ICMP',
                packet_loss_pct REAL DEFAULT 0.0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Create helpful indexes for fast lookup and filtering
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_checks_target ON checks(target);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_checks_status ON checks(status);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_checks_created_at ON checks(created_at DESC);"
        )
        conn.commit()


def save_check(check_data: Dict[str, Any], db_path: Optional[str] = None) -> int:
    """
    Persist a network check record into the database.
    Returns the newly inserted row ID.
    """
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO checks (
                target, resolved_ip, status, response_time_ms, method, packet_loss_pct, error_message, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                check_data.get("target"),
                check_data.get("resolved_ip"),
                check_data.get("status", "Unknown"),
                check_data.get("response_time_ms"),
                check_data.get("method", "ICMP"),
                check_data.get("packet_loss_pct", 0.0),
                check_data.get("error_message"),
                check_data.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return cursor.lastrowid or 0


def get_history(
    limit: int = 50,
    offset: int = 0,
    target: Optional[str] = None,
    status: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieve paginated check history with optional target and status filters.
    Returns a tuple of (records_list, total_count).
    """
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM checks"
        count_query = "SELECT COUNT(*) AS total FROM checks"
        filters: List[str] = []
        params: List[Any] = []

        if target:
            filters.append("target = ?")
            params.append(target.strip())

        if status and status.lower() != "all":
            filters.append("LOWER(status) = LOWER(?)")
            params.append(status.strip())

        if filters:
            clause = " WHERE " + " AND ".join(filters)
            query += clause
            count_query += clause

        # Get total matching count
        cursor.execute(count_query, params)
        total_row = cursor.fetchone()
        total_count = total_row["total"] if total_row else 0

        # Add ordering and pagination
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        exec_params = list(params) + [limit, offset]

        cursor.execute(query, exec_params)
        rows = cursor.fetchall()

        records = [
            {
                "id": row["id"],
                "target": row["target"],
                "resolved_ip": row["resolved_ip"],
                "status": row["status"],
                "response_time_ms": row["response_time_ms"],
                "method": row["method"],
                "packet_loss_pct": row["packet_loss_pct"],
                "error_message": row["error_message"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

        return records, total_count


def get_statistics(
    target: Optional[str] = None,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate aggregate performance metrics:
    - Total checks, successful checks, failed checks
    - Packet loss percentage = (failed / total) * 100
    - Average, min, and max response time in milliseconds
    - Latest check summary
    """
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()

        where_clause = ""
        params: List[Any] = []
        if target:
            where_clause = " WHERE target = ?"
            params.append(target.strip())

        cursor.execute(
            f"""
            SELECT
                COUNT(*) AS total_checks,
                SUM(CASE WHEN LOWER(status) = 'reachable' THEN 1 ELSE 0 END) AS successful_checks,
                SUM(CASE WHEN LOWER(status) != 'reachable' THEN 1 ELSE 0 END) AS failed_checks,
                AVG(CASE WHEN LOWER(status) = 'reachable' THEN response_time_ms ELSE NULL END) AS avg_response_time,
                MIN(CASE WHEN LOWER(status) = 'reachable' THEN response_time_ms ELSE NULL END) AS min_response_time,
                MAX(CASE WHEN LOWER(status) = 'reachable' THEN response_time_ms ELSE NULL END) AS max_response_time
            FROM checks
            {where_clause}
            """,
            params,
        )

        row = cursor.fetchone()
        total = row["total_checks"] if row and row["total_checks"] is not None else 0
        success = row["successful_checks"] if row and row["successful_checks"] is not None else 0
        failed = row["failed_checks"] if row and row["failed_checks"] is not None else 0

        # Calculate estimated packet loss
        packet_loss = round((failed / total) * 100, 2) if total > 0 else 0.0

        avg_rt = round(row["avg_response_time"], 2) if row and row["avg_response_time"] is not None else None
        min_rt = round(row["min_response_time"], 2) if row and row["min_response_time"] is not None else None
        max_rt = round(row["max_response_time"], 2) if row and row["max_response_time"] is not None else None

        # Fetch latest check
        cursor.execute(
            f"SELECT * FROM checks {where_clause} ORDER BY id DESC LIMIT 1",
            params,
        )
        latest_row = cursor.fetchone()
        latest = dict(latest_row) if latest_row else None

        return {
            "target": target or "All Targets",
            "total_checks": total,
            "successful_checks": success,
            "failed_checks": failed,
            "packet_loss_pct": packet_loss,
            "avg_response_time_ms": avg_rt,
            "min_response_time_ms": min_rt,
            "max_response_time_ms": max_rt,
            "latest_check": latest,
        }


def clear_history(target: Optional[str] = None, db_path: Optional[str] = None) -> int:
    """
    Purge records from the database.
    If target is provided, clears history for that specific target only.
    Otherwise clears all history. Returns number of rows deleted.
    """
    path = get_db_path(db_path)
    with get_connection(path) as conn:
        cursor = conn.cursor()
        if target:
            cursor.execute("DELETE FROM checks WHERE target = ?", (target.strip(),))
        else:
            cursor.execute("DELETE FROM checks")
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
