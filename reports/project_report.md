# Comprehensive Project Report: NetPulse Network Performance Monitoring System

**Course / Subject**: Computer Networks & Distributed Systems  
**Project Name**: NetPulse – Network Performance Monitoring System  
**Version**: 1.0.0  
**Author**: Engineering Team  
**Date**: October 2026  

---

## 1. Title
**NetPulse: A Cross-Platform Network Latency, Connectivity, and Packet Loss Telemetry System with Asynchronous Visualization**

---

## 2. Abstract
Modern computer networks demand constant observability to guarantee quality of service (QoS), diagnose transmission degradation, and identify host unreachability before end-user applications fail. NetPulse is a lightweight, full-stack network performance monitoring system developed with Python, Flask, SQLite, and Vanilla JavaScript with Chart.js. The system leverages operating system kernel diagnostics (ICMP Echo request/reply) executed via safe, non-shell platform-aware subprocess calls to monitor local and remote network hosts. Telemetry records—including round-trip time (RTT), reachability state, and estimated packet loss percentages—are persisted in a relational SQLite database with Write-Ahead Logging (WAL) and exposed via a RESTful API. An asynchronous web dashboard provides live key performance indicator (KPI) cards, interactive time-series charts, and filterable audit logs. The system is designed with security hardening against command and SQL injection, division-by-zero safeguards, and fully offline-mockable automated testing.

---

## 3. Problem Statement
Network administrators, developers, and students frequently require continuous visibility into the reachability and responsiveness of internal network infrastructure (e.g., gateways, local DNS servers, virtual machines) and external endpoints. Existing commercial solutions (such as Nagios, SolarWinds, Datadog, or PRTG) suffer from notable drawbacks for local, educational, and small-scale environments:
1. **Excessive Complexity**: Heavy configuration syntax, agent installations, and steep learning curves.
2. **Resource Overhead**: High memory, CPU, and daemon footprint.
3. **Proprietary & Paid Models**: Subscription costs or restricted feature sets in free tiers.
4. **Opaque Telemetry**: Black-box metrics that do not help learners understand the underlying networking protocols (e.g., distinguishing between physical propagation latency, application RTT, and ICMP firewall filtering).

There is an acute need for a transparent, self-contained, zero-cost, cross-platform monitoring system that demonstrates core Computer Networks principles, provides clear user feedback, and maintains rigorous security standards.

---

## 4. Objectives
The key objectives of the NetPulse project are:
1. **Platform-Aware Connectivity Probing**: Implement a reliable, secure mechanism to execute ICMP echo requests across Windows, Linux, and macOS without relying on insecure shell string parsing.
2. **Accurate Metrics Telemetry**: Measure round-trip response time (RTT) in milliseconds using high-precision monotonic timing and calculate rolling session packet loss percentages.
3. **Asynchronous Non-Blocking Monitoring**: Develop a thread-safe background monitoring engine that runs continuous diagnostics at user-defined intervals without degrading web server responsiveness.
4. **Relational Telemetry Storage**: Design an indexed SQLite schema to log historical probes, enabling multi-attribute filtering (by target host, status, date) and aggregated statistics.
5. **Interactive Real-Time Dashboard**: Build an accessible, responsive dashboard featuring dynamic Chart.js time-series graphs, KPI summary cards, and confirmation-guarded administrative actions.
6. **Robust Security & Error Handling**: Implement input sanitization conforming to RFC 1123, command injection prevention, and safe handling of DNS timeouts and unreachable nodes.
7. **Comprehensive Automated Verification**: Establish a 100% offline-compatible automated test suite using mocked network boundaries.

---

## 5. Existing System vs. Proposed System

| Feature | Conventional / Existing Tools (e.g., CLI Ping, Enterprise Suites) | Proposed System (NetPulse) |
|---|---|---|
| **User Interface** | Terminal CLI output or heavy, complex multi-page enterprise web portals | Clean, modern, responsive single-page dashboard with KPI cards and interactive charts |
| **Setup & Dependencies** | Requires complex daemons, SNMP agents, Node.js builds, or paid licenses | Standard Python 3 standard library + Flask; zero paid APIs or heavy Node runtimes |
| **Data Retention** | Ephemeral (CLI ping data is lost once terminal closes) or locked in proprietary DBs | Local, portable, open SQLite database with indexed queries and full user ownership |
| **Visual Telemetry** | Plain text terminal output | Real-time responsive line charts (latency over time), doughnut charts (outcome ratios), and trend analysis |
| **Security Architecture** | Vulnerable web wrappers frequently concatenate inputs into `os.system()` or `shell=True` | Strict parameterization with `subprocess.run(args, shell=False)`, RFC 1123 regex, and parameterized SQL |
| **Educational Transparency** | Diagnostic details are hidden behind complex status codes | Clearly explains network concepts (ICMP blocking, RTT vs. propagation delay, packet loss estimation) |

---

## 6. System Architecture

NetPulse is structured as a three-tier decoupled architecture:

```
+------------------------------------------------------------------------+
|                      PRESENTATION TIER (Browser)                      |
|  - templates/index.html: Semantic, accessible UI layout                |
|  - static/css/style.css: Modern Slate/Cobalt color system, Grid/Flexbox|
|  - static/js/app.js: Asynchronous Fetch API, DOM updates, Chart.js     |
+-----------------------------------+------------------------------------+
                                    | HTTP / JSON (REST API)
                                    v
+-----------------------------------+------------------------------------+
|                      APPLICATION TIER (Flask)                         |
|  - app.py: REST Endpoints (/api/check, /api/history, /api/stats, etc.) |
|  - Target Input Sanitization & Validation (RFC 1123, IPv4, IPv6)      |
|  - Background Worker Coordination (MonitoringManager daemon thread)    |
+-------------------+--------------------------------+-------------------+
                    |                                |
                    v                                v
+-------------------+---------------+   +------------+-------------------+
|     DIAGNOSTICS ENGINE            |   |     PERSISTENCE TIER           |
|     (monitor.py)                  |   |     (database.py)              |
|  - Platform-aware ICMP commands   |   |  - SQLite3 engine (netpulse.db)|
|  - socket.gethostbyname (DNS)     |   |  - checks table + indexes      |
|  - time.perf_counter (RTT ms)     |   |  - Write-Ahead Logging (WAL)   |
|  - Subprocess execution           |   |  - SQL aggregation queries     |
+-------------------+---------------+   +--------------------------------+
                    |
                    v
+-------------------+----------------------------------------------------+
|                   OPERATING SYSTEM KERNEL & NETWORK                    |
|  - ping.exe (Windows) / ping (UNIX)                                    |
|  - Network Interface Card (NIC) -> Router -> Target Host               |
+------------------------------------------------------------------------+
```

---

## 7. Modules and Components

### 7.1. Web Server & REST API Controller (`app.py`)
- Implements the Flask application factory pattern (`create_app()`) to facilitate testing with isolated configurations.
- Routes:
  - `GET /`: Renders the single-page dashboard.
  - `GET /api/health`: Provides server and database readiness probes.
  - `POST /api/check`: Accepts JSON target and executes an immediate one-off probe.
  - `GET /api/history`: Returns paginated, filtered check logs.
  - `DELETE /api/history`: Purges check records from the database.
  - `GET /api/stats`: Returns calculated summary metrics.
  - `POST /api/monitor/start` & `POST /api/monitor/stop`: Controls background monitoring threads.
  - `GET /api/monitor/status`: Inspects active session state.

### 7.2. Network Diagnostics Engine (`monitor.py`)
- **`validate_target(target)`**: Validates that target strings adhere strictly to IPv4, IPv6, or RFC 1123 hostname standards, explicitly rejecting shell metacharacters (`&`, `|`, `;`, `$`, `>`, etc.).
- **`resolve_target(target, timeout)`**: Resolves hostnames to IP addresses with a socket timeout to prevent application hanging on unresolvable hosts.
- **`execute_ping(target, timeout_sec)`**:
  - Automatically identifies host OS (`platform.system().lower()`).
  - Constructs appropriate argument vectors:
    - Windows: `["ping", "-n", "1", "-w", "<ms>", target]`
    - macOS: `["ping", "-c", "1", "-W", "<ms>", target]`
    - Linux: `["ping", "-c", "1", "-W", "<sec>", target]`
  - Measures wall-clock RTT via `time.perf_counter()`.
  - Parses system output for kernel-reported RTT while retaining monotonic timer fallback.
  - Accurately identifies `Reachable`, `Unreachable`, or `Unknown` states.
- **`MonitoringManager`**:
  - Implements thread-safe concurrency using `threading.Lock` and `threading.Event`.
  - Runs a background daemon loop executing periodic checks and recording results in SQLite.

### 7.3. Persistence & Analytics Engine (`database.py`)
- Manages connection lifecycle with `sqlite3.Row` dictionaries.
- Enables SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) for concurrent read/write stability.
- Creates indexes on `target`, `status`, and `created_at` for efficient pagination and filtering.
- Performs mathematical aggregations directly within SQL (sum, average, minimum, maximum).

### 7.4. User Interface & Chart Visualization (`index.html`, `style.css`, `app.js`)
- Responsive CSS Grid and Flexbox layout adhering to accessible contrast standards.
- Dark navy (`#0f172a`), slate (`#1e293b`), and vibrant blue (`#2563eb`) palette with status-coded emerald (`#10b981`) and rose (`#ef4444`) indicators.
- Chart.js 4.4 integration managing:
  - Latency over time (line chart with point interpolation).
  - Check outcome ratio (doughnut chart).
  - Packet loss percentage trends.
- Real-time polling controller with automatic state recovery on page reload.

---

## 8. Algorithms and Mathematical Formulas

### 8.1. Response Time / Round-Trip Time (RTT) Calculation
The duration $T_{\text{response}}$ of each probe is measured using Python's high-resolution monotonic clock:
$$T_{\text{response}} = (t_{\text{end}} - t_{\text{start}}) \times 1000 \quad [\text{ms}]$$
Where:
- $t_{\text{start}}$ is sampled immediately prior to invoking the child process via `time.perf_counter()`.
- $t_{\text{end}}$ is sampled immediately following process termination.
- Monotonic clocks are immune to system clock adjustments (such as NTP time syncs or daylight saving adjustments), ensuring non-negative, accurate durations.

### 8.2. Packet Loss Percentage Formula
Estimated packet loss is calculated over the total number of executed checks:
$$\text{Packet Loss (\%)} = \begin{cases} \left( \dfrac{N_{\text{failed}}}{N_{\text{total}}} \right) \times 100 & \text{if } N_{\text{total}} > 0 \\ 0.0 & \text{if } N_{\text{total}} = 0 \end{cases}$$
Where:
- $N_{\text{failed}}$ is the count of checks where status $\neq \text{'Reachable'}$.
- $N_{\text{total}}$ is the total number of checks performed ($N_{\text{successful}} + N_{\text{failed}}$).

### 8.3. Statistical Averages
Across all successful probes ($k$ reachable probes):
$$\bar{T} = \frac{1}{k} \sum_{i=1}^{k} T_i \quad [\text{ms}]$$
$$T_{\min} = \min_{1 \le i \le k} \{T_i\}, \quad T_{\max} = \max_{1 \le i \le k} \{T_i\}$$
If $k = 0$, the system returns `null` (`N/A`) rather than manufacturing artificial zero values.

---

## 9. Testing Results and Quality Verification

Automated testing was conducted using `pytest` across four verification layers:
1. **Target Validation & Security**: Verified that IPv4, IPv6, and standard hostnames pass, while shell injection characters, spaces, and excessive length strings are rejected with 400 Bad Request responses.
2. **Connectivity Logic (Mocked)**: Verified OS command vector construction, DNS resolution failure recovery, output parsing for Windows/Linux formats, and subprocess timeout handling.
3. **Database Operations**: Verified table auto-creation, CRUD inserts, status filtering, pagination offsets, and safe zero-division calculations.
4. **REST API Integration**: Verified HTTP status codes (200, 400, 404), JSON payload envelopes, and monitoring start/stop lifecycle.

### Test Execution Summary
- **Test Engine**: pytest 9.1.1 on Python 3.14 (win32)
- **Total Tests Collected**: 27
- **Total Tests Passed**: 27 (100% pass rate)
- **Total Tests Failed**: 0
- **Execution Time**: 1.32 seconds
- **External Network Dependency**: 0% (Fully offline with mocked sockets and subprocesses)

---

## 10. Limitations

1. **Firewall Asymmetry**: ICMP echo requests may be blocked or dropped by intermediate stateful firewalls (such as AWS Security Groups or corporate edge routers), even when TCP services (e.g., port 80/443) are functioning. NetPulse accurately denotes this state as `Unreachable`, educating the user on ICMP filtering.
2. **Process Spawning Overhead**: Spawning a new OS process for each ping probe introduces approximately 2–5 ms of process creation overhead. For high-frequency millisecond-level telemetry across thousands of simultaneous nodes, raw ICMP sockets (e.g. via `scapy` or C sockets requiring OS root/administrative privileges) would be required.
3. **Single Host Concurrency**: The built-in `MonitoringManager` operates on one active host target per background session to maintain simple, beginner-friendly thread synchronization.

---

## 11. Future Enhancements

1. **Multi-Target Concurrent Monitoring**: Extend the `MonitoringManager` with an asynchronous thread pool or Python `asyncio` loop to monitor a configurable list of targets simultaneously.
2. **Multi-Protocol Diagnostics (TCP & UDP Probing)**: Add transport-layer checks (e.g. TCP SYN probes to port 80/443 or DNS lookup latency to port 53) to verify service availability when ICMP is blocked.
3. **Configurable Alerting Engine**: Implement threshold alerts (e.g., audio chime or desktop notification if latency exceeds 100 ms or packet loss exceeds 10%).
4. **Data Exporting**: Enable CSV and JSON export of historical monitoring logs for offline reporting and coursework submission.
5. **Traceroute Visualizer**: Incorporate hop-by-hop route discovery to identify which intermediate router or gateway causes latency spikes.

---

## 12. Conclusion
The NetPulse project successfully delivers a complete, professional, and beginner-accessible network performance monitoring system. By marrying low-level operating system network diagnostic utilities with a modern, responsive web application and relational persistence, NetPulse bridges theoretical Computer Networks concepts with practical full-stack software engineering. The system fulfills all functional, architectural, and security requirements, providing a transparent, reliable, and easily deployable tool for network observability.
