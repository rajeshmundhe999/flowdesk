// FlowDesk Frontend Application Logic

let currentTicket = null;
let debounceTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  fetchTickets();
  loadIncidents();
  loadKB();
});

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.add("hidden");
  });
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("border-indigo-500", "text-indigo-400");
    btn.classList.add("border-transparent", "text-slate-400");
  });

  const activePanel = document.getElementById(tabId);
  if (activePanel) activePanel.classList.remove("hidden");

  const activeBtn = document.getElementById(`tab-btn-${tabId.replace("tab-", "")}`);
  if (activeBtn) {
    activeBtn.classList.add("border-indigo-500", "text-indigo-400");
    activeBtn.classList.remove("border-transparent", "text-slate-400");
  }

  if (tabId === "tab-eval") {
    loadEvaluationBenchmark();
  }
}

// Stats Loading
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    document.getElementById("stat-total").innerText = data.total_tickets || 0;
    document.getElementById("stat-incidents").innerText = data.incidents_count || 0;
    const crit = (data.severity_breakdown?.P0 || 0) + (data.severity_breakdown?.P1 || 0);
    document.getElementById("stat-critical").innerText = crit;
  } catch (err) {
    console.error("Error loading stats:", err);
  }
}

// Fetch & Filter Tickets
function debounceFilter() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(fetchTickets, 300);
}

async function fetchTickets() {
  const search = document.getElementById("filter-search").value.trim();
  const cat = document.getElementById("filter-category").value;
  const sev = document.getElementById("filter-severity").value;
  const plat = document.getElementById("filter-platform").value;
  const tier = document.getElementById("filter-tier").value;

  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (cat) params.append("category", cat);
  if (sev) params.append("severity", sev);
  if (plat) params.append("platform", plat);
  if (tier) params.append("plan_tier", tier);

  try {
    const res = await fetch(`/api/tickets?${params.toString()}`);
    const tickets = await res.json();
    renderTicketsTable(tickets);
  } catch (err) {
    console.error("Error fetching tickets:", err);
  }
}

function renderTicketsTable(tickets) {
  const tbody = document.getElementById("tickets-table-body");
  document.getElementById("ticket-count").innerText = tickets.length;
  tbody.innerHTML = "";

  if (tickets.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-500">No tickets match active filters.</td></tr>`;
    return;
  }

  tickets.forEach((t) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-800/50 cursor-pointer transition";
    tr.onclick = () => openTicketModal(t.id);

    // Badges
    const sevColor = {
      P0: "bg-red-500/10 text-red-400 border-red-500/20",
      P1: "bg-rose-500/10 text-rose-400 border-rose-500/20",
      P2: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      P3: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    }[t.severity] || "bg-slate-800 text-slate-400";

    const sentIcon = {
      frustrated: '<i class="fa-solid fa-face-frown text-rose-400" title="Frustrated"></i>',
      satisfied: '<i class="fa-solid fa-face-smile text-emerald-400" title="Satisfied"></i>',
      neutral: '<i class="fa-solid fa-face-meh text-slate-400" title="Neutral"></i>',
    }[t.sentiment] || "-";

    tr.innerHTML = `
      <td class="px-4 py-3 font-mono text-slate-400 font-medium">${t.id}</td>
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-medium capitalize">${t.platform}</span></td>
      <td class="px-4 py-3 max-w-md">
        <p class="font-medium text-slate-200 truncate">${escapeHtml(t.subject)}</p>
        <p class="text-slate-400 text-[11px] truncate mt-0.5">${escapeHtml(t.body.substring(0, 80))}...</p>
      </td>
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">${t.category || "untriaged"}</span></td>
      <td class="px-4 py-3"><span class="px-2 py-0.5 rounded border text-[11px] font-semibold ${sevColor}">${t.severity || "--"}</span></td>
      <td class="px-4 py-3 text-center text-sm">${sentIcon}</td>
      <td class="px-4 py-3">
        <div class="flex items-center gap-1.5">
          <span class="text-[11px] text-slate-400">${t.confidence ? (t.confidence * 100).toFixed(0) + '%' : '--'}</span>
          <span class="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">${t.triage_method || 'none'}</span>
        </div>
      </td>
      <td class="px-4 py-3 text-right">
        <button class="px-2.5 py-1 text-[11px] font-medium rounded bg-slate-800 hover:bg-slate-700 text-slate-200">View</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Modal Details & Action Flows
async function openTicketModal(ticketId) {
  try {
    const res = await fetch(`/api/tickets/${ticketId}`);
    currentTicket = await res.json();

    document.getElementById("modal-ticket-id").innerText = currentTicket.id;
    document.getElementById("modal-ticket-subject").innerText = currentTicket.subject;
    document.getElementById("modal-platform").innerText = `${currentTicket.platform} (${currentTicket.os_version})`;
    document.getElementById("modal-version").innerText = currentTicket.app_version;
    document.getElementById("modal-tier").innerText = currentTicket.plan_tier.toUpperCase();
    document.getElementById("modal-severity").innerText = currentTicket.severity || "--";
    document.getElementById("modal-body").innerText = currentTicket.body;
    document.getElementById("modal-triage-method").innerText = currentTicket.triage_method || "rules";
    document.getElementById("modal-triage-reason").innerText = currentTicket.triage_reason || "No triage metadata";

    document.getElementById("action-output-area").classList.add("hidden");
    document.getElementById("modal-ticket").classList.remove("hidden");
  } catch (err) {
    console.error("Error opening ticket:", err);
  }
}

function closeModal() {
  document.getElementById("modal-ticket").classList.add("hidden");
}

async function generateReplyForCurrentTicket() {
  if (!currentTicket) return;
  try {
    const res = await fetch(`/api/tickets/${currentTicket.id}/reply`, { method: "POST" });
    const data = await res.json();

    const outputArea = document.getElementById("action-output-area");
    const outputTitle = document.getElementById("action-output-title");
    const outputContent = document.getElementById("action-output-content");

    outputTitle.innerHTML = `<span class="flex items-center gap-1.5"><i class="fa-solid fa-user-check text-emerald-400"></i> Empathetic Reply Draft (Human Review Required — Anti-Promise Verified)</span>`;
    outputContent.innerText = data.draft_text;
    outputArea.classList.remove("hidden");
  } catch (err) {
    console.error("Error generating reply:", err);
  }
}

async function generateBugReportForCurrentTicket() {
  if (!currentTicket) return;
  try {
    const res = await fetch(`/api/tickets/${currentTicket.id}/report`);
    const data = await res.json();

    const outputArea = document.getElementById("action-output-area");
    const outputTitle = document.getElementById("action-output-title");
    const outputContent = document.getElementById("action-output-content");

    outputTitle.innerHTML = `<span class="flex items-center gap-1.5"><i class="fa-solid fa-bug text-indigo-400"></i> Structured Engineering Bug Report</span>`;
    outputContent.innerText = data.markdown_report;
    outputArea.classList.remove("hidden");
  } catch (err) {
    console.error("Error generating bug report:", err);
  }
}

function copyActionOutput() {
  const content = document.getElementById("action-output-content").innerText;
  navigator.clipboard.writeText(content).then(() => {
    alert("Copied to clipboard!");
  });
}

// Batch Triage
async function runBatchTriage() {
  try {
    const res = await fetch("/api/triage/batch", { method: "POST" });
    const data = await res.json();
    await loadStats();
    await fetchTickets();
    await loadIncidents();
    alert(`Batch triage complete. ${data.triaged} tickets triaged, ${data.incidents_detected} incidents detected.`);
  } catch (err) {
    console.error("Batch triage error:", err);
  }
}

// Incidents
async function loadIncidents() {
  try {
    const res = await fetch("/api/incidents");
    const incidents = await res.json();
    renderIncidents(incidents);
  } catch (err) {
    console.error("Error loading incidents:", err);
  }
}

async function runIncidentDetection() {
  try {
    const res = await fetch("/api/incidents/detect", { method: "POST" });
    const data = await res.json();
    renderIncidents(data.incidents);
    loadStats();
    alert(`Incident detection complete. ${data.incidents_detected} active clusters identified.`);
  } catch (err) {
    console.error("Incident detection error:", err);
  }
}

function renderIncidents(incidents) {
  const container = document.getElementById("incidents-container");
  container.innerHTML = "";

  if (incidents.length === 0) {
    container.innerHTML = `<div class="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center text-slate-500 text-xs">No active incident clusters detected.</div>`;
    return;
  }

  incidents.forEach((inc) => {
    const card = document.createElement("div");
    card.className = "bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3";

    const sevColor = {
      P0: "bg-red-500/10 text-red-400 border-red-500/20",
      P1: "bg-rose-500/10 text-rose-400 border-rose-500/20",
      P2: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      P3: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    }[inc.severity] || "bg-slate-800 text-slate-300";

    card.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2.5">
          <span class="px-2 py-0.5 rounded border text-xs font-semibold ${sevColor}">${inc.severity}</span>
          <h3 class="font-semibold text-white text-sm">${escapeHtml(inc.title)}</h3>
          <span class="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-xs font-medium">${inc.ticket_count} tickets</span>
        </div>
        <button onclick="viewIncidentReport('${inc.id}')" class="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center gap-1.5">
          <i class="fa-solid fa-file-waveform"></i> Generate Incident Bug Report
        </button>
      </div>
      <p class="text-xs text-slate-300 leading-relaxed">${escapeHtml(inc.summary)}</p>
      <div class="flex items-center gap-4 text-[11px] text-slate-500">
        <span><strong class="text-slate-400">Signal:</strong> <code>${escapeHtml(inc.signature)}</code></span>
        <span><strong class="text-slate-400">Platforms:</strong> ${inc.affected_platforms.join(", ")}</span>
        <span><strong class="text-slate-400">Versions:</strong> ${inc.affected_versions.join(", ")}</span>
      </div>
    `;
    container.appendChild(card);
  });
}

async function viewIncidentReport(incidentId) {
  try {
    const res = await fetch(`/api/incidents/${incidentId}/report`);
    const data = await res.json();

    // Show inside modal
    document.getElementById("modal-ticket-id").innerText = data.incident_id;
    document.getElementById("modal-ticket-subject").innerText = data.title;
    document.getElementById("modal-platform").innerText = "Multiple Clustered";
    document.getElementById("modal-version").innerText = "Multiple Clustered";
    document.getElementById("modal-tier").innerText = "ALL";
    document.getElementById("modal-severity").innerText = "AGGREGATED";
    document.getElementById("modal-body").innerText = `Engineering bug report for incident cluster ${data.incident_id}`;
    document.getElementById("modal-triage-method").innerText = "clustering";
    document.getElementById("modal-triage-reason").innerText = "Synthesized from pattern detection algorithm (3+ matching tickets)";

    const outputArea = document.getElementById("action-output-area");
    const outputTitle = document.getElementById("action-output-title");
    const outputContent = document.getElementById("action-output-content");

    outputTitle.innerHTML = `<span class="flex items-center gap-1.5"><i class="fa-solid fa-fire-flame-curved text-rose-400"></i> Probable Incident Bug Report (Engineering Ready)</span>`;
    outputContent.innerText = data.markdown_report;
    outputArea.classList.remove("hidden");

    document.getElementById("modal-ticket").classList.remove("hidden");
  } catch (err) {
    console.error("Error viewing incident report:", err);
  }
}

// Knowledge Base
async function loadKB() {
  try {
    const res = await fetch("/api/kb");
    const articles = await res.json();
    const container = document.getElementById("kb-container");
    container.innerHTML = "";

    articles.forEach((a) => {
      const card = document.createElement("div");
      card.className = "bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2.5";
      card.innerHTML = `
        <div class="flex items-center justify-between">
          <h4 class="font-semibold text-white text-sm">${escapeHtml(a.title)}</h4>
          <span class="font-mono text-[10px] text-slate-500">${a.filename}</span>
        </div>
        <div>
          <span class="text-[11px] font-semibold text-slate-400 block mb-0.5">Symptom</span>
          <p class="text-xs text-slate-300 line-clamp-2">${escapeHtml(a.symptom)}</p>
        </div>
        <div>
          <span class="text-[11px] font-semibold text-slate-400 block mb-0.5">Confirmed Fix</span>
          <p class="text-xs text-slate-300 line-clamp-3">${escapeHtml(a.fix)}</p>
        </div>
        <div class="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
          <span class="text-emerald-400 font-medium"><i class="fa-solid fa-lock text-[10px]"></i> Data Safe</span>
          <span class="text-slate-500">Tier 1-3 Support Spec</span>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading KB:", err);
  }
}

// Diagnostics Helper
async function runDiagnosticsFromUI() {
  const btn = document.getElementById("btn-run-diag");
  const container = document.getElementById("diagnostics-results");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> Probing...`;

  try {
    const res = await fetch("/api/diagnose");
    const results = await res.json();

    let html = `
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
            <tr>
              <th class="px-4 py-2.5">Endpoint Target</th>
              <th class="px-4 py-2.5">DNS Resolution</th>
              <th class="px-4 py-2.5">TLS Handshake</th>
              <th class="px-4 py-2.5">HTTP Probe</th>
              <th class="px-4 py-2.5">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800 text-slate-300">
    `;

    results.forEach((r) => {
      const slowBadge = r.is_slow ? `<span class="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px]">SLOW</span>` : "";
      html += `
        <tr class="hover:bg-slate-800/30">
          <td class="px-4 py-3 font-medium text-slate-200">${escapeHtml(r.target_name)}<br><span class="text-[10px] font-mono text-slate-500">${r.host}</span></td>
          <td class="px-4 py-3"><span class="px-2 py-0.5 rounded ${r.dns.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'} font-semibold text-[10px]">${r.dns.status}</span> <span class="text-slate-400 text-[11px]">${r.dns.latency_ms}ms</span><br><span class="text-[10px] text-slate-500">${r.dns.info}</span></td>
          <td class="px-4 py-3"><span class="px-2 py-0.5 rounded ${r.tls.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'} font-semibold text-[10px]">${r.tls.status}</span> <span class="text-slate-400 text-[11px]">${r.tls.latency_ms}ms</span><br><span class="text-[10px] text-slate-500">${r.tls.info}</span></td>
          <td class="px-4 py-3"><span class="px-2 py-0.5 rounded ${r.http.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'} font-semibold text-[10px]">${r.http.status}</span> <span class="text-slate-400 text-[11px]">${r.http.latency_ms}ms</span><br><span class="text-[10px] text-slate-500">${r.http.info}</span></td>
          <td class="px-4 py-3">${slowBadge || '<span class="text-emerald-400 font-medium">HEALTHY</span>'}</td>
        </tr>
      `;
    });

    html += `</tbody></table></div>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p class="text-rose-400 text-xs">Error running diagnostics: ${err}</p>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-play text-xs"></i> Run Diagnostic Probe`;
  }
}

// Benchmark Evaluation
async function loadEvaluationBenchmark() {
  const container = document.getElementById("eval-container");
  container.innerHTML = `<p class="text-xs text-slate-400">Loading ground-truth benchmark calculation...</p>`;

  try {
    const res = await fetch("/api/evaluate");
    const data = await res.json();

    let html = `
      <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <p class="text-xs text-slate-400 font-medium">Category Accuracy</p>
          <p class="text-2xl font-bold text-emerald-400 mt-1">${data.category_accuracy}%</p>
          <p class="text-[11px] text-slate-500 mt-0.5">Across ${data.total} labeled test cases</p>
        </div>
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <p class="text-xs text-slate-400 font-medium">Severity Accuracy</p>
          <p class="text-2xl font-bold text-indigo-400 mt-1">${data.severity_accuracy}%</p>
          <p class="text-[11px] text-slate-500 mt-0.5">P0 to P3 prioritization</p>
        </div>
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
          <p class="text-xs text-slate-400 font-medium">Misclassification Count</p>
          <p class="text-2xl font-bold text-amber-400 mt-1">${data.misclassifications.length}</p>
          <p class="text-[11px] text-slate-500 mt-0.5">Boundaries documented below</p>
        </div>
      </div>

      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <h3 class="font-semibold text-white text-sm">Category Performance Metrics</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th class="px-4 py-2">Category</th>
                <th class="px-4 py-2">Precision</th>
                <th class="px-4 py-2">Recall</th>
                <th class="px-4 py-2">F1-Score</th>
                <th class="px-4 py-2">Support</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-800 text-slate-300">
    `;

    for (const [cat, m] of Object.entries(data.metrics_per_category)) {
      if (m.support > 0) {
        html += `
          <tr>
            <td class="px-4 py-2 font-medium text-slate-200">${cat}</td>
            <td class="px-4 py-2">${m.precision}%</td>
            <td class="px-4 py-2">${m.recall}%</td>
            <td class="px-4 py-2 font-semibold text-indigo-300">${m.f1}%</td>
            <td class="px-4 py-2 text-slate-500">${m.support}</td>
          </tr>
        `;
      }
    }

    html += `</tbody></table></div></div>`;

    // Misclassifications Breakdown
    html += `
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-3">
        <h3 class="font-semibold text-white text-sm">Honest Breakdown of Misclassified Edge Cases</h3>
        <div class="space-y-2">
    `;

    data.misclassifications.forEach((m) => {
      html += `
        <div class="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1">
          <div class="flex items-center justify-between">
            <span class="font-mono text-slate-400 font-semibold">${m.id}</span>
            <span class="text-[11px] text-slate-400">Expected: <strong class="text-emerald-400">${m.expected_category}</strong> &rarr; Predicted: <strong class="text-rose-400">${m.predicted_category}</strong> (Conf: ${m.confidence})</span>
          </div>
          <p class="text-slate-300 font-medium">"${escapeHtml(m.subject)}"</p>
          <p class="text-[11px] text-slate-500">${escapeHtml(m.reason)}</p>
        </div>
      `;
    });

    html += `</div></div>`;
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<p class="text-rose-400 text-xs">Error loading evaluation: ${err}</p>`;
  }
}

// Create New Ticket / Log Bug Handlers
function openCreateTicketModal() {
  document.getElementById("create-ticket-form").reset();
  document.getElementById("modal-create-ticket").classList.remove("hidden");
}

function closeCreateTicketModal() {
  document.getElementById("modal-create-ticket").classList.add("hidden");
}

async function submitNewTicket(event) {
  event.preventDefault();
  const submitBtn = document.getElementById("btn-submit-ticket");
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> Ingesting...`;

  const payload = {
    subject: document.getElementById("new-ticket-subject").value.trim(),
    body: document.getElementById("new-ticket-body").value.trim(),
    platform: document.getElementById("new-ticket-platform").value,
    plan_tier: document.getElementById("new-ticket-tier").value,
    app_version: document.getElementById("new-ticket-app-ver").value.trim() || "1.4.3",
    os_version: document.getElementById("new-ticket-os-ver").value.trim() || "Windows 11",
    channel: "in-app",
  };

  try {
    const res = await fetch("/api/tickets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Failed to create ticket: ${res.statusText}`);
    }

    const newTicket = await res.json();
    closeCreateTicketModal();

    // Refresh UI
    await loadStats();
    await fetchTickets();
    await loadIncidents();

    // Open ticket details modal immediately so user sees the real-time triage
    openTicketModal(newTicket.id);
  } catch (err) {
    alert(`Error logging ticket: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<i class="fa-solid fa-bolt"></i> Ingest & Auto-Triage`;
  }
}

// Utility
function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
