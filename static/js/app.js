/**
 * NetPulse - Network Performance Monitoring System
 * Vanilla JavaScript ES6+ Frontend Controller
 * Handles real-time polling, Chart.js visualization, REST API communication, and UI state.
 */

document.addEventListener("DOMContentLoaded", () => {
  // =========================================================================
  // State Management
  // =========================================================================
  const state = {
    isMonitoring: false,
    activeTarget: "",
    pollTimer: null,
    pollIntervalMs: 3000,
    currentPage: 1,
    pageSize: 15,
    totalRecords: 0,
    charts: {
      latency: null,
      outcome: null,
      loss: null,
    },
    latencyHistory: [], // Max 25 points for chart
    lossHistory: [],
  };

  // =========================================================================
  // DOM Elements
  // =========================================================================
  const elements = {
    // Header & Clock
    systemStatusBadge: document.getElementById("systemStatusBadge"),
    systemStatusText: document.getElementById("systemStatusText"),
    liveClock: document.getElementById("liveClock"),

    // Active Banner
    activeMonitoringBanner: document.getElementById("activeMonitoringBanner"),
    bannerTarget: document.getElementById("bannerTarget"),
    bannerInterval: document.getElementById("bannerInterval"),
    bannerCount: document.getElementById("bannerCount"),
    bannerStopBtn: document.getElementById("bannerStopBtn"),

    // Form Controls
    targetInput: document.getElementById("targetInput"),
    intervalSelect: document.getElementById("intervalSelect"),
    startBtn: document.getElementById("startBtn"),
    stopBtn: document.getElementById("stopBtn"),
    checkNowBtn: document.getElementById("checkNowBtn"),
    quickButtons: document.querySelectorAll(".btn-tag"),

    // KPI Cards
    kpiStatus: document.getElementById("kpiStatus"),
    kpiTargetName: document.getElementById("kpiTargetName"),
    kpiAvgRt: document.getElementById("kpiAvgRt"),
    kpiAvgRtUnit: document.getElementById("kpiAvgRtUnit"),
    kpiMinMaxRt: document.getElementById("kpiMinMaxRt"),
    kpiPacketLoss: document.getElementById("kpiPacketLoss"),
    kpiTotalChecks: document.getElementById("kpiTotalChecks"),
    kpiSuccessCount: document.getElementById("kpiSuccessCount"),
    kpiFailCount: document.getElementById("kpiFailCount"),

    // Charts & Empty States
    latencyCanvas: document.getElementById("latencyChart"),
    outcomeCanvas: document.getElementById("outcomeChart"),
    lossCanvas: document.getElementById("packetLossChart"),
    latencyEmptyState: document.getElementById("latencyEmptyState"),
    outcomeEmptyState: document.getElementById("outcomeEmptyState"),
    lossEmptyState: document.getElementById("lossEmptyState"),

    // Table & Filters
    historyTableBody: document.getElementById("historyTableBody"),
    filterTarget: document.getElementById("filterTarget"),
    filterStatus: document.getElementById("filterStatus"),
    applyFiltersBtn: document.getElementById("applyFiltersBtn"),
    resetFiltersBtn: document.getElementById("resetFiltersBtn"),
    refreshHistoryBtn: document.getElementById("refreshHistoryBtn"),
    clearHistoryBtn: document.getElementById("clearHistoryBtn"),

    // Pagination
    prevPageBtn: document.getElementById("prevPageBtn"),
    nextPageBtn: document.getElementById("nextPageBtn"),
    currentPageIndicator: document.getElementById("currentPageIndicator"),
    paginationInfo: document.getElementById("paginationInfo"),

    // Modal
    confirmModal: document.getElementById("confirmModal"),
    cancelModalBtn: document.getElementById("cancelModalBtn"),
    confirmClearBtn: document.getElementById("confirmClearBtn"),

    // Toasts
    toastContainer: document.getElementById("toastContainer"),
  };

  // =========================================================================
  // Initialize Application
  // =========================================================================
  init();

  function init() {
    startClock();
    checkHealth();
    initCharts();
    setupEventListeners();
    checkCurrentMonitoringSession();
    fetchHistory();
    fetchStats();
  }

  // =========================================================================
  // Clock & Health Polling
  // =========================================================================
  function startClock() {
    function update() {
      const now = new Date();
      elements.liveClock.textContent = now.toUTCString().slice(17, 25) + " UTC";
    }
    update();
    setInterval(update, 1000);
  }

  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      const dot = elements.systemStatusBadge.querySelector(".status-dot");
      if (res.ok && data.success) {
        dot.className = "status-dot online";
        elements.systemStatusText.textContent = "Server Online";
      } else {
        dot.className = "status-dot offline";
        elements.systemStatusText.textContent = "Degraded";
      }
    } catch (e) {
      const dot = elements.systemStatusBadge.querySelector(".status-dot");
      dot.className = "status-dot offline";
      elements.systemStatusText.textContent = "Server Offline";
    }
  }

  // =========================================================================
  // Chart.js Setup & Updates
  // =========================================================================
  function initCharts() {
    if (typeof Chart === "undefined") {
      console.warn("Chart.js not loaded. Visual charts will be unavailable.");
      return;
    }

    // Common Chart styling options
    const commonScales = {
      x: {
        grid: { color: "rgba(226, 232, 240, 0.6)" },
        ticks: { font: { family: "'JetBrains Mono', monospace", size: 10 } },
      },
      y: {
        beginAtZero: true,
        grid: { color: "rgba(226, 232, 240, 0.6)" },
        ticks: { font: { family: "'JetBrains Mono', monospace", size: 10 } },
      },
    };

    // 1. Latency Line Chart
    state.charts.latency = new Chart(elements.latencyCanvas, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Response Time (ms)",
            data: [],
            borderColor: "#2563eb",
            backgroundColor: "rgba(37, 99, 235, 0.08)",
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 6,
            pointBackgroundColor: "#2563eb",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `Response Time: ${ctx.parsed.y} ms`,
            },
          },
        },
        scales: commonScales,
      },
    });

    // 2. Outcome Ratio Doughnut Chart
    state.charts.outcome = new Chart(elements.outcomeCanvas, {
      type: "doughnut",
      data: {
        labels: ["Reachable", "Unreachable"],
        datasets: [
          {
            data: [0, 0],
            backgroundColor: ["#10b981", "#ef4444"],
            hoverOffset: 4,
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { boxWidth: 12, font: { size: 11 } },
          },
        },
        cutout: "70%",
      },
    });

    // 3. Packet Loss Trend Line Chart
    state.charts.loss = new Chart(elements.lossCanvas, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "Packet Loss (%)",
            data: [],
            borderColor: "#ef4444",
            backgroundColor: "rgba(239, 68, 68, 0.1)",
            borderWidth: 2,
            tension: 0.25,
            fill: true,
            pointRadius: 3,
            pointHoverRadius: 5,
            pointBackgroundColor: "#ef4444",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => `Packet Loss: ${ctx.parsed.y}%`,
            },
          },
        },
        scales: {
          ...commonScales,
          y: {
            ...commonScales.y,
            max: 100,
          },
        },
      },
    });
  }

  function updateChartsData(records) {
    if (!state.charts.latency || !records || records.length === 0) {
      if (elements.latencyEmptyState) elements.latencyEmptyState.classList.remove("hidden");
      if (elements.lossEmptyState) elements.lossEmptyState.classList.remove("hidden");
      return;
    }

    // Records are ordered DESC from DB, so reverse for chronological chart view
    const chronRecords = [...records].reverse().slice(-20);

    const labels = chronRecords.map((r) => {
      const parts = (r.created_at || "").split(" ");
      return parts.length > 1 ? parts[1].slice(0, 8) : r.created_at;
    });

    const latencies = chronRecords.map((r) => (r.status === "Reachable" ? r.response_time_ms : null));
    const losses = chronRecords.map((r) => r.packet_loss_pct || 0);

    // Update Latency Chart
    state.charts.latency.data.labels = labels;
    state.charts.latency.data.datasets[0].data = latencies;
    state.charts.latency.update();

    if (elements.latencyEmptyState) elements.latencyEmptyState.classList.add("hidden");

    // Update Loss Chart
    state.charts.loss.data.labels = labels;
    state.charts.loss.data.datasets[0].data = losses;
    state.charts.loss.update();

    if (elements.lossEmptyState) elements.lossEmptyState.classList.add("hidden");
  }

  function updateOutcomeChart(successCount, failCount) {
    if (!state.charts.outcome) return;

    if (successCount === 0 && failCount === 0) {
      if (elements.outcomeEmptyState) elements.outcomeEmptyState.classList.remove("hidden");
      state.charts.outcome.data.datasets[0].data = [0, 0];
    } else {
      if (elements.outcomeEmptyState) elements.outcomeEmptyState.classList.add("hidden");
      state.charts.outcome.data.datasets[0].data = [successCount, failCount];
    }
    state.charts.outcome.update();
  }

  // =========================================================================
  // Event Listeners
  // =========================================================================
  function setupEventListeners() {
    // Quick-select preset buttons
    elements.quickButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        elements.targetInput.value = btn.dataset.target;
        elements.targetInput.focus();
      });
    });

    // One-Off Check
    elements.checkNowBtn.addEventListener("click", executeSingleCheck);

    // Start Monitoring
    elements.startBtn.addEventListener("click", startMonitoring);

    // Stop Monitoring
    elements.stopBtn.addEventListener("click", stopMonitoring);
    elements.bannerStopBtn.addEventListener("click", stopMonitoring);

    // History Table Actions
    elements.refreshHistoryBtn.addEventListener("click", () => {
      fetchHistory();
      fetchStats();
      showToast("History data refreshed.", "info");
    });

    elements.applyFiltersBtn.addEventListener("click", () => {
      state.currentPage = 1;
      fetchHistory();
    });

    elements.resetFiltersBtn.addEventListener("click", () => {
      elements.filterTarget.value = "";
      elements.filterStatus.value = "all";
      state.currentPage = 1;
      fetchHistory();
    });

    // Pagination
    elements.prevPageBtn.addEventListener("click", () => {
      if (state.currentPage > 1) {
        state.currentPage--;
        fetchHistory();
      }
    });

    elements.nextPageBtn.addEventListener("click", () => {
      const maxPages = Math.ceil(state.totalRecords / state.pageSize) || 1;
      if (state.currentPage < maxPages) {
        state.currentPage++;
        fetchHistory();
      }
    });

    // Clear History Modal
    elements.clearHistoryBtn.addEventListener("click", () => {
      elements.confirmModal.classList.remove("hidden");
    });

    elements.cancelModalBtn.addEventListener("click", () => {
      elements.confirmModal.classList.add("hidden");
    });

    elements.confirmClearBtn.addEventListener("click", executeClearHistory);
  }

  // =========================================================================
  // API Operations
  // =========================================================================

  /**
   * Execute a single one-off connectivity check
   */
  async function executeSingleCheck() {
    const target = elements.targetInput.value.trim();
    if (!target) {
      showToast("Please enter a hostname or IP address.", "warning");
      elements.targetInput.focus();
      return;
    }

    setButtonLoading(elements.checkNowBtn, true, "Checking...");
    try {
      const res = await fetch("/api/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: target, save: true }),
      });

      const json = await res.json();
      if (!res.ok || !json.success) {
        showToast(json.error || "Check failed.", "error");
        return;
      }

      const result = json.data;
      updateKpisFromCheck(result);
      fetchHistory();
      fetchStats(target);

      const statusMsg = result.status === "Reachable" 
        ? `${target} responded in ${result.response_time_ms} ms.` 
        : `${target} is ${result.status}: ${result.error_message || "No response"}`;
      showToast(statusMsg, result.status === "Reachable" ? "success" : "error");

    } catch (e) {
      showToast(`Network error: ${e.message}`, "error");
    } finally {
      setButtonLoading(elements.checkNowBtn, false, "Check Now");
    }
  }

  /**
   * Start background continuous monitoring
   */
  async function startMonitoring() {
    const target = elements.targetInput.value.trim();
    const interval = parseInt(elements.intervalSelect.value, 10) || 5;

    if (!target) {
      showToast("Please enter a valid hostname or IP address to monitor.", "warning");
      elements.targetInput.focus();
      return;
    }

    setButtonLoading(elements.startBtn, true, "Starting...");
    try {
      const res = await fetch("/api/monitor/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target, interval }),
      });

      const json = await res.json();
      if (!res.ok || !json.success) {
        showToast(json.error || json.message || "Could not start monitoring.", "error");
        return;
      }

      state.isMonitoring = true;
      state.activeTarget = target;
      state.pollIntervalMs = Math.max(2000, interval * 1000);

      updateMonitoringUI(true, target, interval);
      showToast(`Started monitoring ${target} every ${interval}s.`, "success");

      // Start periodic polling
      startPolling();

    } catch (e) {
      showToast(`Failed to start monitoring: ${e.message}`, "error");
    } finally {
      setButtonLoading(elements.startBtn, false, "Start Monitoring");
    }
  }

  /**
   * Stop background continuous monitoring
   */
  async function stopMonitoring() {
    setButtonLoading(elements.stopBtn, true, "Stopping...");
    try {
      const res = await fetch("/api/monitor/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const json = await res.json();
      state.isMonitoring = false;
      stopPolling();
      updateMonitoringUI(false);

      showToast(json.message || "Monitoring stopped.", "info");
      fetchHistory();
      fetchStats(state.activeTarget);

    } catch (e) {
      showToast(`Error stopping monitor: ${e.message}`, "error");
    } finally {
      setButtonLoading(elements.stopBtn, false, "Stop Monitoring");
    }
  }

  /**
   * Check if a monitoring session is already active (e.g. after page refresh)
   */
  async function checkCurrentMonitoringSession() {
    try {
      const res = await fetch("/api/monitor/status");
      const json = await res.json();
      if (res.ok && json.success && json.data.is_running) {
        state.isMonitoring = true;
        state.activeTarget = json.data.target;
        elements.targetInput.value = json.data.target;
        elements.intervalSelect.value = json.data.interval;
        state.pollIntervalMs = Math.max(2000, json.data.interval * 1000);

        updateMonitoringUI(true, json.data.target, json.data.interval, json.data.total_checks);
        startPolling();
      }
    } catch (e) {
      console.error("Failed to query monitor status:", e);
    }
  }

  /**
   * Polling loop for active monitoring
   */
  function startPolling() {
    stopPolling();
    state.pollTimer = setInterval(async () => {
      try {
        const res = await fetch("/api/monitor/status");
        const json = await res.json();
        if (json.success && json.data.is_running) {
          elements.bannerCount.textContent = json.data.total_checks;
          if (json.data.last_check) {
            updateKpisFromCheck(json.data.last_check);
          }
          fetchHistory(false); // Silent fetch without resetting page
          fetchStats(state.activeTarget);
        } else if (state.isMonitoring) {
          // Stopped remotely
          stopMonitoring();
        }
      } catch (e) {
        console.warn("Polling tick error:", e);
      }
    }, state.pollIntervalMs);
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  /**
   * Fetch check history records from server
   */
  async function fetchHistory(updateCharts = true) {
    const offset = (state.currentPage - 1) * state.pageSize;
    const targetFilter = elements.filterTarget.value.trim();
    const statusFilter = elements.filterStatus.value;

    let url = `/api/history?limit=${state.pageSize}&offset=${offset}`;
    if (targetFilter) url += `&target=${encodeURIComponent(targetFilter)}`;
    if (statusFilter && statusFilter !== "all") url += `&status=${encodeURIComponent(statusFilter)}`;

    try {
      const res = await fetch(url);
      const json = await res.json();
      if (res.ok && json.success) {
        const records = json.data.records;
        state.totalRecords = json.data.total;
        renderHistoryTable(records);
        updatePagination();

        if (updateCharts) {
          updateChartsData(records);
        }
      }
    } catch (e) {
      console.error("Error fetching history:", e);
    }
  }

  /**
   * Fetch aggregate performance statistics
   */
  async function fetchStats(target = null) {
    const active = target || elements.targetInput.value.trim() || null;
    let url = "/api/stats";
    if (active) url += `?target=${encodeURIComponent(active)}`;

    try {
      const res = await fetch(url);
      const json = await res.json();
      if (res.ok && json.success) {
        renderStats(json.data);
      }
    } catch (e) {
      console.error("Error fetching stats:", e);
    }
  }

  /**
   * Execute clear history in SQLite
   */
  async function executeClearHistory() {
    elements.confirmModal.classList.add("hidden");
    try {
      const res = await fetch("/api/history", { method: "DELETE" });
      const json = await res.json();
      if (res.ok && json.success) {
        showToast(json.message, "success");
        state.currentPage = 1;
        fetchHistory();
        fetchStats();

        // Reset KPIs
        elements.kpiStatus.textContent = "Idle";
        elements.kpiStatus.className = "kpi-value";
        elements.kpiTargetName.textContent = "History purged";
        elements.kpiAvgRt.textContent = "N/A";
        elements.kpiAvgRtUnit.textContent = "";
        elements.kpiMinMaxRt.textContent = "Min: N/A | Max: N/A";
        elements.kpiPacketLoss.textContent = "0.0%";
        elements.kpiTotalChecks.textContent = "0";
        elements.kpiSuccessCount.textContent = "0";
        elements.kpiFailCount.textContent = "0";

        updateOutcomeChart(0, 0);
      } else {
        showToast(json.error || "Failed to clear history.", "error");
      }
    } catch (e) {
      showToast(`Error: ${e.message}`, "error");
    }
  }

  // =========================================================================
  // UI Rendering & DOM Updates
  // =========================================================================

  function updateMonitoringUI(isRunning, target = "", interval = 5, count = 0) {
    if (isRunning) {
      elements.activeMonitoringBanner.classList.remove("hidden");
      elements.bannerTarget.textContent = target;
      elements.bannerInterval.textContent = interval;
      elements.bannerCount.textContent = count;
      elements.startBtn.disabled = true;
      elements.stopBtn.disabled = false;
      elements.targetInput.disabled = true;
      elements.intervalSelect.disabled = true;
    } else {
      elements.activeMonitoringBanner.classList.add("hidden");
      elements.startBtn.disabled = false;
      elements.stopBtn.disabled = true;
      elements.targetInput.disabled = false;
      elements.intervalSelect.disabled = false;
    }
  }

  function updateKpisFromCheck(check) {
    if (!check) return;

    elements.kpiTargetName.textContent = `${check.target} (${check.resolved_ip || "unresolved"})`;

    if (check.status === "Reachable") {
      elements.kpiStatus.textContent = "Reachable";
      elements.kpiStatus.className = "kpi-value status-badge badge-reachable";
    } else if (check.status === "Unreachable") {
      elements.kpiStatus.textContent = "Unreachable";
      elements.kpiStatus.className = "kpi-value status-badge badge-unreachable";
    } else {
      elements.kpiStatus.textContent = check.status || "Unknown";
      elements.kpiStatus.className = "kpi-value status-badge badge-unknown";
    }
  }

  function renderStats(stats) {
    if (!stats) return;

    elements.kpiTotalChecks.textContent = stats.total_checks.toLocaleString();
    elements.kpiSuccessCount.textContent = stats.successful_checks.toLocaleString();
    elements.kpiFailCount.textContent = stats.failed_checks.toLocaleString();

    // Packet Loss Percentage
    elements.kpiPacketLoss.textContent = `${stats.packet_loss_pct}%`;
    if (stats.packet_loss_pct > 20) {
      elements.kpiPacketLoss.style.color = "var(--color-danger)";
    } else if (stats.packet_loss_pct > 0) {
      elements.kpiPacketLoss.style.color = "var(--color-warning-dark)";
    } else {
      elements.kpiPacketLoss.style.color = "var(--color-success-dark)";
    }

    // Response times
    if (stats.avg_response_time_ms !== null) {
      elements.kpiAvgRt.textContent = stats.avg_response_time_ms;
      elements.kpiAvgRtUnit.textContent = "ms";
      elements.kpiMinMaxRt.textContent = `Min: ${stats.min_response_time_ms} ms | Max: ${stats.max_response_time_ms} ms`;
    } else {
      elements.kpiAvgRt.textContent = "N/A";
      elements.kpiAvgRtUnit.textContent = "";
      elements.kpiMinMaxRt.textContent = "Min: N/A | Max: N/A";
    }

    // Update Outcome Chart
    updateOutcomeChart(stats.successful_checks, stats.failed_checks);
  }

  function renderHistoryTable(records) {
    const tbody = elements.historyTableBody;
    tbody.innerHTML = "";

    if (!records || records.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="table-empty-message">
            No monitoring records found matching current criteria.
          </td>
        </tr>
      `;
      return;
    }

    records.forEach((row) => {
      const tr = document.createElement("tr");

      let statusBadgeClass = "badge-unknown";
      if (row.status === "Reachable") statusBadgeClass = "badge-reachable";
      else if (row.status === "Unreachable") statusBadgeClass = "badge-unreachable";

      const rtDisplay = row.response_time_ms !== null 
        ? `<strong>${row.response_time_ms}</strong> ms` 
        : "<span class='text-muted'>N/A</span>";

      const lossDisplay = `${row.packet_loss_pct || 0}%`;
      const noteDisplay = row.error_message || row.details || (row.status === "Reachable" ? "Echo reply received" : "No response");

      tr.innerHTML = `
        <td class="mono-cell text-muted">#${row.id}</td>
        <td class="mono-cell">${escapeHtml(row.created_at)}</td>
        <td><strong>${escapeHtml(row.target)}</strong></td>
        <td class="mono-cell">${escapeHtml(row.resolved_ip || "--")}</td>
        <td><span class="status-badge ${statusBadgeClass}">${escapeHtml(row.status)}</span></td>
        <td class="mono-cell">${rtDisplay}</td>
        <td class="mono-cell">${lossDisplay}</td>
        <td><span class="badge badge-info">${escapeHtml(row.method || "ICMP")}</span></td>
        <td title="${escapeHtml(noteDisplay)}">${escapeHtml(truncate(noteDisplay, 50))}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function updatePagination() {
    const startIdx = state.totalRecords === 0 ? 0 : (state.currentPage - 1) * state.pageSize + 1;
    const endIdx = Math.min(state.currentPage * state.pageSize, state.totalRecords);
    const maxPages = Math.ceil(state.totalRecords / state.pageSize) || 1;

    elements.paginationInfo.textContent = `Showing ${startIdx} to ${endIdx} of ${state.totalRecords} entries`;
    elements.currentPageIndicator.textContent = `Page ${state.currentPage} of ${maxPages}`;

    elements.prevPageBtn.disabled = state.currentPage <= 1;
    elements.nextPageBtn.disabled = state.currentPage >= maxPages;
  }

  // =========================================================================
  // Helpers: Toasts, Loading States, Sanitization
  // =========================================================================

  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 250);
    }, 4000);
  }

  function setButtonLoading(btn, isLoading, text) {
    btn.disabled = isLoading;
    if (isLoading) {
      btn.dataset.originalHtml = btn.innerHTML;
      btn.innerHTML = `
        <svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
        </svg>
        ${text}
      `;
    } else {
      if (btn.dataset.originalHtml) {
        btn.innerHTML = btn.dataset.originalHtml;
      }
    }
  }

  function truncate(str, maxLen = 40) {
    if (!str) return "";
    return str.length > maxLen ? str.slice(0, maxLen) + "…" : str;
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
