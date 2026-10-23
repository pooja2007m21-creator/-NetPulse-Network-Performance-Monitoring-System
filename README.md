# NetPulse – Network Performance Monitoring System

NetPulse is a lightweight, professional, full-stack network performance monitoring and diagnostics web application. Built with **Python 3, Flask, SQLite, Vanilla JavaScript (ES6+), and Chart.js**, NetPulse empowers system administrators, network engineers, and students to measure host connectivity, track response times (RTT), monitor packet loss, and visualize network stability through real-time interactive charts and historical audit logs.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [Technologies Used](#technologies-used)
4. [System Architecture](#system-architecture)
5. [Folder Structure](#folder-structure)
6. [Prerequisites](#prerequisites)
7. [Windows Setup & Installation Guide](#windows-setup--installation-guide)
8. [Running the Application](#running-the-application)
9. [Running Automated Tests](#running-automated-tests)
10. [REST API Documentation](#rest-api-documentation)
11. [Computer Networking Concepts Learned](#computer-networking-concepts-learned)
12. [Troubleshooting Common Issues](#troubleshooting-common-issues)
13. [GitHub Upload Instructions](#github-upload-instructions)
14. [Deployment Options & Limitations](#deployment-options--limitations)
15. [Beginner's Code Reading Guide](#beginners-code-reading-guide)

---

## Project Overview

In computer networking, maintaining reliable communication between nodes requires continuous observation of latency, reachability, and packet transmission health. NetPulse was developed as a clean, transparent, dependency-light solution to demystify how network telemetry is gathered from the operating system kernel and presented on a modern web dashboard.

NetPulse executes **platform-aware ICMP Echo probes** (using Python's `subprocess` without shell invocation for bulletproof security), stores telemetry in **SQLite**, calculates vital metrics such as **packet loss percentage** and **round-trip time (RTT)**, and dynamically updates **Chart.js** data visualizations via asynchronous polling.

---

## Key Features

- **Executive KPI Dashboard**: Live summary cards showing current host status (`Reachable`, `Unreachable`, `Unknown`, `Idle`), average response time, packet loss percentage, and successful vs. failed check counts.
- **Continuous Background Monitoring**: Dedicated Python background worker thread executes scheduled probes at configurable intervals (1s to 300s) without blocking web requests.
- **One-Off Instant Diagnostics**: "Check Now" button executes an immediate probe for quick troubleshooting without starting an interval loop.
- **Real-Time Interactive Visualizations**:
  - **Response Time Line Chart**: Millisecond latency timeline over time.
  - **Packet Loss Trend Chart**: Percentage loss curve.
  - **Outcome Distribution Chart**: Doughnut chart showing Reachable vs. Unreachable ratio.
- **Audit History & Logs**: Paginated data table storing target, resolved IP, status, response time, timestamp, and diagnostic notes in SQLite.
- **Search & Filter Tools**: Instant filtering by target hostname/IP and connection status.
- **Preset Quick Targets**: One-click quick selection for `127.0.0.1` (Localhost), `8.8.8.8` (Google Public DNS), `1.1.1.1` (Cloudflare DNS), and `example.com` (IANA).
- **Hardened Security**:
  - RFC 1123 hostname & IPv4/IPv6 validation.
  - Strict prevention of command injection by using argument lists with `shell=False`.
  - Input sanitization against shell metacharacters (`&`, `|`, `;`, `$`, `>`, etc.).
  - Database parameterization against SQL injection.
- **Zero Paid Dependencies**: Runs completely on free, open-source technologies with no proprietary cloud accounts or API keys needed.

---

## Technologies Used

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend UI** | HTML5, CSS3, Vanilla JavaScript (ES6+) | Semantic layout, responsive styling, asynchronous DOM manipulation |
| **Data Visualization** | Chart.js 4.4 | Canvas-based responsive time-series and doughnut charts |
| **Backend Framework** | Python 3, Flask 3.x | Lightweight WSGI web framework and REST API routing |
| **Database** | SQLite3 (Python standard library) | Relational persistence for telemetry records with WAL mode |
| **System Diagnostics** | Python `subprocess`, `socket`, `platform` | Kernel-level ICMP ping execution and DNS hostname resolution |
| **Automated Testing** | pytest 8.x / 9.x | Unit and integration testing with mocked I/O |

---

## System Architecture

```
+------------------------------------------------------------------+
|                   Client Browser (User Interface)                |
|  - HTML5 / CSS3 Responsive Dashboard (Desktop, Tablet, Mobile)   |
|  - Vanilla JavaScript ES6+ Controller (State, Polling, Toasts)  |
|  - Chart.js Visualizations (Latency Line, Outcome Doughnut)      |
+---------------------------------+--------------------------------+
                                  |
                           HTTP / REST API
                       (JSON over HTTP/1.1)
                                  |
                                  v
+---------------------------------+--------------------------------+
|                   Flask Web Server (app.py)                     |
|  - Routing: Dashboard & REST API Endpoints                       |
|  - Security & Target Validation Layer                            |
|  - Request Lifecycle & JSON Error Envelopes                      |
+-----------------+-------------------------------+----------------+
                  |                               |
                  v                               v
+-----------------+---------------+   +-----------+----------------+
|    Monitor Engine (monitor.py)   |   |   Database (database.py)   |
|  - validate_target()            |   |  - SQLite3 (netpulse.db)   |
|  - resolve_target() (DNS)       |   |  - schema: checks table    |
|  - execute_ping()               |   |  - CRUD & Aggregations     |
|  - MonitoringManager (Thread)   |   |  - WAL mode concurrency    |
+-----------------+---------------+   +----------------------------+
                  |
        Platform-Aware Execution
      (subprocess with shell=False)
                  |
                  v
+-----------------+------------------------------------------------+
|             Operating System Kernel (Windows / Linux / macOS)    |
|  - ping.exe (Windows: -n 1 -w <ms>)                              |
|  - ICMP Echo Request -> IP Network -> ICMP Echo Reply            |
+------------------------------------------------------------------+
```

---

## Folder Structure

```
NetPulse/
│
├── app.py                     # Main Flask web application & REST API routes
├── monitor.py                 # Platform-aware ping execution & background thread manager
├── database.py                # SQLite schema definition, queries, and statistics aggregation
├── requirements.txt           # Python package dependencies
├── README.md                  # Comprehensive documentation and student guide
├── .gitignore                 # Git ignore rules for virtual environments, caches, and DBs
│
├── templates/
│   └── index.html             # Single-page dashboard HTML template
│
├── static/
│   ├── css/
│   │   └── style.css          # Modern dark-navy & cobalt blue responsive styles
│   └── js/
│       └── app.js             # Vanilla ES6+ frontend controller & Chart.js logic
│
├── tests/
│   └── test_app.py            # Complete pytest test suite (27 tests, 100% offline mocked)
│
├── reports/
│   └── project_report.md      # Formal academic and engineering project report
│
└── data/
    └── .gitkeep               # Preserves data directory structure in Git
```

---

## Prerequisites

Before starting, ensure your Windows PC has:
1. **Windows 10 or Windows 11**
2. **Python 3.10+** (Python 3.13 or 3.14 recommended)
   - To check if Python is installed, open Windows PowerShell and run:
     ```powershell
     py --version
     ```
     If installed, it will print e.g. `Python 3.14.x` or `Python 3.13.x`.
3. **Internet connection** (only needed once to install Python packages; the application itself runs completely locally offline).

---

## Windows Setup & Installation Guide

Follow these exact steps in **Windows PowerShell**:

### Step 1: Open PowerShell and Navigate to the Project Folder
```powershell
cd "C:\Users\pooja\.gemini\antigravity\scratch\NetPulse"
```

### Step 2: Create a Python Virtual Environment
Creating a virtual environment ensures NetPulse dependencies do not conflict with other Python projects on your machine:
```powershell
py -m venv .venv
```

### Step 3: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```
> **Note for Windows Users:** If PowerShell displays an execution policy error such as `Execution_Policies`, run this one-time command in PowerShell to permit local scripts:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then run `.\.venv\Scripts\Activate.ps1` again. You will see `(.venv)` in your terminal prompt.

### Step 4: Upgrade pip and Install Dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## Running the Application

To launch the NetPulse server, execute:
```powershell
python app.py
```

You will see output similar to:
```text
==================================================
 NetPulse Network Performance Monitoring System
 Dashboard: http://127.0.0.1:5000/
 Health check: http://127.0.0.1:5000/api/health
==================================================
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

### Opening the Dashboard
Open your web browser (Chrome, Edge, Firefox, or Brave) and navigate to:
```
http://127.0.0.1:5000/
```

### How to Use the Dashboard
1. **Quick Test**: Click the `127.0.0.1 (Localhost)` or `8.8.8.8 (Google DNS)` button under Safe Test Targets.
2. **Single Check**: Click **Check Now** to run an instant one-off ping. Look at the KPI cards and the Activity Table update immediately.
3. **Continuous Monitoring**: Select an interval (e.g. `2 seconds` or `5 seconds`) and click **Start Monitoring**.
   - Notice the blue **Active Monitoring** banner appear with a live pulsing beacon.
   - Watch the **Response Time History** and **Packet Loss Trend** charts update smoothly as new probes complete.
4. **Stop Monitoring**: Click **Stop Monitoring** at any time to halt background probes cleanly.
5. **Search & Filter**: Type an IP or choose a status (`Reachable` or `Unreachable`) in the History toolbar and click **Apply Filters**.
6. **Clear History**: Click **Clear History**, then confirm in the popup modal to wipe local SQLite logs.

---

## Running Automated Tests

NetPulse includes a test suite covering unit validation, network mocking, database transactions, formulas, and REST API routes. All network calls are mocked, so tests run in ~1.3 seconds with zero external internet dependencies.

In your PowerShell terminal (with the virtual environment active):
```powershell
pytest -v
```

Expected result:
```text
tests/test_app.py::TestValidationAndSecurity::test_valid_ipv4_addresses PASSED
tests/test_app.py::TestValidationAndSecurity::test_valid_hostnames PASSED
tests/test_app.py::TestValidationAndSecurity::test_valid_ipv6 PASSED
tests/test_app.py::TestValidationAndSecurity::test_reject_empty_or_whitespace PASSED
tests/test_app.py::TestValidationAndSecurity::test_reject_command_injection_attempts PASSED
tests/test_app.py::TestValidationAndSecurity::test_reject_excessive_length PASSED
tests/test_app.py::TestConnectivityChecks::test_dns_resolution_success PASSED
tests/test_app.py::TestConnectivityChecks::test_dns_resolution_failure PASSED
tests/test_app.py::TestConnectivityChecks::test_parse_ping_output_formats PASSED
tests/test_app.py::TestConnectivityChecks::test_execute_ping_reachable PASSED
tests/test_app.py::TestConnectivityChecks::test_execute_ping_unreachable PASSED
tests/test_app.py::TestConnectivityChecks::test_execute_ping_timeout_exception PASSED
tests/test_app.py::TestDatabaseAndMetrics::test_init_and_save_check PASSED
tests/test_app.py::TestDatabaseAndMetrics::test_statistics_calculation_with_checks PASSED
tests/test_app.py::TestDatabaseAndMetrics::test_statistics_empty_state_division_by_zero_safe PASSED
tests/test_app.py::TestDatabaseAndMetrics::test_history_filtering_by_status_and_target PASSED
tests/test_app.py::TestDatabaseAndMetrics::test_clear_history PASSED
tests/test_app.py::TestRestApiEndpoints::test_dashboard_index_route PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_health_endpoint PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_check_valid_target PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_check_invalid_target_rejected PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_check_empty_payload PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_history_and_pagination PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_stats_endpoint PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_delete_history PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_monitor_lifecycle PASSED
tests/test_app.py::TestRestApiEndpoints::test_api_not_found_handler PASSED

============================= 27 passed in 1.32s ==============================
```

---

## REST API Documentation

All API requests and responses use standard `application/json` with HTTP status codes:
- `200 OK`: Successful operation
- `400 Bad Request`: Validation failure or invalid parameters
- `404 Not Found`: Endpoint or resource not found
- `500 Internal Server Error`: Unhandled server exception

### 1. Health Status
- **Method**: `GET`
- **Route**: `/api/health`
- **Description**: Returns server readiness and SQLite database status.
- **Example Response**:
  ```json
  {
    "success": true,
    "status": "online",
    "application": "NetPulse Network Performance Monitor",
    "version": "1.0.0",
    "database": "healthy"
  }
  ```

### 2. Immediate One-Off Check
- **Method**: `POST`
- **Route**: `/api/check`
- **Description**: Runs a single platform-aware ICMP ping probe against a target.
- **Request Body**:
  ```json
  {
    "target": "8.8.8.8",
    "save": true
  }
  ```
- **Example Response (Success)**:
  ```json
  {
    "success": true,
    "data": {
      "id": 14,
      "target": "8.8.8.8",
      "resolved_ip": "8.8.8.8",
      "status": "Reachable",
      "response_time_ms": 18.42,
      "method": "ICMP",
      "packet_loss_pct": 0.0,
      "error_message": null,
      "details": "Host responded in 18.42 ms. ICMP Echo Reply received."
    }
  }
  ```

### 3. Monitoring Session Management
- **Start Background Monitoring**:
  - **Method**: `POST`
  - **Route**: `/api/monitor/start`
  - **Request Body**: `{"target": "1.1.1.1", "interval": 5}`
  - **Response**: `{"success": true, "message": "Monitoring started for '1.1.1.1' every 5s.", "session": {...}}`
- **Stop Background Monitoring**:
  - **Method**: `POST`
  - **Route**: `/api/monitor/stop`
  - **Response**: `{"success": true, "message": "Monitoring stopped for '1.1.1.1'.", "session": {...}}`
- **Query Session Status**:
  - **Method**: `GET`
  - **Route**: `/api/monitor/status`
  - **Response**:
    ```json
    {
      "success": true,
      "data": {
        "is_running": true,
        "target": "1.1.1.1",
        "interval": 5,
        "started_at": "2026-10-23 15:00:00 UTC",
        "total_checks": 12,
        "successful_checks": 12,
        "failed_checks": 0,
        "packet_loss_pct": 0.0
      }
    }
    ```

### 4. Monitoring History
- **Method**: `GET`
- **Route**: `/api/history?limit=15&offset=0&target=localhost&status=Reachable`
- **Description**: Returns paginated check logs matching query filters.
- **Example Response**:
  ```json
  {
    "success": true,
    "data": {
      "records": [
        {
          "id": 42,
          "target": "localhost",
          "resolved_ip": "127.0.0.1",
          "status": "Reachable",
          "response_time_ms": 0.45,
          "method": "ICMP",
          "packet_loss_pct": 0.0,
          "error_message": null,
          "created_at": "2026-10-23 14:52:10"
        }
      ],
      "total": 1,
      "limit": 15,
      "offset": 0
    }
  }
  ```

### 5. Clear History
- **Method**: `DELETE`
- **Route**: `/api/history` (Optional query: `?target=127.0.0.1`)
- **Response**: `{"success": true, "message": "Successfully deleted 42 record(s).", "deleted_count": 42}`

### 6. Aggregate Statistics
- **Method**: `GET`
- **Route**: `/api/stats` (Optional query: `?target=8.8.8.8`)
- **Description**: Returns mathematical summaries across recorded checks.
- **Example Response**:
  ```json
  {
    "success": true,
    "data": {
      "target": "8.8.8.8",
      "total_checks": 50,
      "successful_checks": 48,
      "failed_checks": 2,
      "packet_loss_pct": 4.0,
      "avg_response_time_ms": 21.15,
      "min_response_time_ms": 14.20,
      "max_response_time_ms": 58.60,
      "latest_check": {...}
    }
  }
  ```

---

## Computer Networking Concepts Learned

### 1. Response Time vs. Raw Network Latency
- **Raw Network Latency**: The physical propagation delay required for an electrical or optical signal to travel through cables, repeaters, and routers from source to destination.
- **Response Time (Round-Trip Time / RTT)**: The total wall-clock elapsed duration from when a sender transmits a request packet to when the destination host processes it and the reply packet arrives back at the sender. NetPulse measures RTT in milliseconds (`ms`).

### 2. Internet Control Message Protocol (ICMP)
- ICMP is an auxiliary protocol in the Internet Protocol suite (RFC 792) used by network devices to send error messages and operational information.
- The `ping` command generates an **ICMP Type 8 (Echo Request)** packet. If the destination host is online and permits ICMP, it replies with an **ICMP Type 0 (Echo Reply)** packet.

### 3. Why a Failed Ping Does Not Mean a Host is Down
In production networks, firewalls (e.g. Windows Defender Firewall, AWS Security Groups, Cloudflare, corporate perimeter firewalls) often drop ICMP Echo requests to protect against denial-of-service (DDoS) ping floods or network mapping. Therefore, NetPulse reports unanswering hosts as **Unreachable** rather than definitively "Offline", and educates the user that transport-layer ports (such as HTTP port 80 or HTTPS port 443) may still be responsive.

### 4. Estimating Packet Loss
In real-time network streams (VoIP, video calls, competitive gaming), dropped packets degrade quality. NetPulse calculates session packet loss using the formula:
$$\text{Packet Loss (\%)} = \left( \frac{\text{Failed Checks}}{\text{Total Checks}} \right) \times 100$$
To guarantee reliability, NetPulse protects against division by zero when zero checks have occurred ($0.0\%$).

---

## Troubleshooting Common Issues

### 1. `ping` reports "Destination host unreachable" or "Request timed out"
- Check your local internet connectivity.
- Verify whether the target host or your local Wi-Fi router blocks ICMP packets.
- Test with `127.0.0.1` (loopback) to verify your local TCP/IP stack is functioning.

### 2. PowerShell says `cannot be loaded because running scripts is disabled`
- Run this one-time command in PowerShell:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
  Then re-run `.\.venv\Scripts\Activate.ps1`.

### 3. Port 5000 is already in use
- If another application occupies port 5000, specify a different port when running:
  ```powershell
  $env:PORT="5050"; python app.py
  ```
  Then open `http://127.0.0.1:5050/`.

---

## GitHub Upload Instructions

To publish your NetPulse project to your personal GitHub profile:

1. **Initialize Git inside the project directory**:
   ```powershell
   cd "C:\Users\pooja\.gemini\antigravity\scratch\NetPulse"
   git init
   ```

2. **Check Status**:
   ```powershell
   git status
   ```
   Notice that `.venv`, `__pycache__`, and `*.db` are automatically ignored by `.gitignore`.

3. **Stage and Commit all source files**:
   ```powershell
   git add .
   git commit -m "Initial commit: NetPulse Network Performance Monitoring System"
   ```

4. **Create a new empty repository on GitHub**:
   - Go to [GitHub.com](https://github.com) and click **New Repository**.
   - Name it `NetPulse` (do not initialize with a README since we already have one).

5. **Connect your local project to GitHub and push**:
   ```powershell
   git branch -M main
   git remote add origin https://github.com/<YOUR-GITHUB-USERNAME>/NetPulse.git
   git push -u origin main
   ```

---

## Deployment Options & Limitations

### Deployment Options
- **Local / On-Premise**: Run locally using Python on any workstation or home lab server.
- **Production WSGI Server**: For production environments, wrap Flask with **Waitress** on Windows or **Gunicorn** on Linux:
  ```powershell
  python -m pip install waitress
  waitress-serve --port=5000 app:app
  ```
- **Containerization (Docker)**: Can be easily containerized into an Alpine Python image with `ENTRYPOINT ["python", "app.py"]`. Note that container ping requires `NET_RAW` Linux capability (`--cap-add=NET_RAW`).

### Known Limitations
- ICMP echo execution requires the operating system's built-in `ping` command.
- In shared cloud hosting environments (like certain serverless functions), raw ICMP sockets or subprocess calls to `ping` may be prohibited by the host hypervisor. In such environments, TCP port probing (`socket.connect_ex`) is used as an alternative.
- Background monitoring is hosted in-process using daemon threads. For enterprise multi-node deployments with hundreds of concurrent targets, a task queue like Celery with Redis would be recommended.

---

## Beginner's Code Reading Guide

If you are new to programming or computer networking, explore the files in this order:

1. **`monitor.py`**:
   - Start here to understand how Python talks to the operating system. Look at `validate_target()` for regex security and `execute_ping()` to see how `subprocess.run(["ping", ...])` is called safely.
2. **`database.py`**:
   - Learn how SQLite tables are created and how `save_check()` and `get_statistics()` calculate averages and packet loss percentages using SQL.
3. **`app.py`**:
   - See how Flask maps HTTP URLs (like `/api/check` and `/api/history`) to Python functions and returns JSON responses.
4. **`templates/index.html`** & **`static/css/style.css`**:
   - Inspect the clean layout, KPI cards, and responsive CSS grid design.
5. **`static/js/app.js`**:
   - Discover how JavaScript uses `fetch()` to call the Flask API, renders table rows, and feeds real-time latency points to Chart.js.
6. **`tests/test_app.py`**:
   - Learn how professionals test network code using `unittest.mock` to simulate ping replies without touching real cables or WiFi.
#   - N e t P u l s e - N e t w o r k - P e r f o r m a n c e - M o n i t o r i n g - S y s t e m  
 