const API = "";
const REPORT_STORAGE_KEY = "maintenanceReportCurrent";
const REPORT_HISTORY_KEY = "maintenanceReportHistory";
const CHAT_STORAGE_KEY = "maintenanceChatHistory";
const OLLAMA_URL_KEY = "maintenanceOllamaUrl";
const STORAGE_VERSION = 1;
const MAX_HISTORY = 12;

let chatHistory = [];
let reportBlocks = [];
let summaryMarkdown = "";
let currentSummary = null;
let sessionId = sessionStorage.getItem("maintenanceSessionId") || null;
let saveReportTimer = null;
let restoredFromStorage = false;

const $ = (sel) => document.querySelector(sel);
const reportEl = $("#report-content");
const chatEl = $("#chat-messages");
const statusBadge = $("#status-badge");
const sourceBadge = $("#source-badge");
const modelSelect = $("#model-select");
const mdPreviewSelect = $("#md-preview-select");
const ollamaDialog = $("#ollama-settings-dialog");
const ollamaUrlInput = $("#ollama-url-input");
const ollamaSettingsStatus = $("#ollama-settings-status");
const docPreviewDialog = $("#doc-preview-dialog");
const docPreviewBody = $("#doc-preview-body");
const docPreviewTitle = $("#doc-preview-title");
let viewMode = "live"; // "live" | "preview"
let ollamaBaseUrl = localStorage.getItem(OLLAMA_URL_KEY) || "";
let defaultOllamaUrl = "http://localhost:11434";

function formatINR(n) {
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000) return `₹${(n / 1000).toFixed(0)}K`;
  return `₹${n}`;
}

function apiHeaders(json = true) {
  const h = {};
  if (json) h["Content-Type"] = "application/json";
  if (sessionId) h["X-Session-Id"] = sessionId;
  if (ollamaBaseUrl) h["X-Ollama-Url"] = ollamaBaseUrl;
  return h;
}

function normalizeClientOllamaUrl(url) {
  return (url || "").trim().replace(/\/+$/, "");
}

function getOllamaUrl() {
  return normalizeClientOllamaUrl(ollamaBaseUrl) || defaultOllamaUrl;
}

function setOllamaUrl(url, persist = true) {
  ollamaBaseUrl = normalizeClientOllamaUrl(url);
  if (persist) {
    if (ollamaBaseUrl && ollamaBaseUrl !== defaultOllamaUrl) {
      localStorage.setItem(OLLAMA_URL_KEY, ollamaBaseUrl);
    } else {
      localStorage.removeItem(OLLAMA_URL_KEY);
      ollamaBaseUrl = "";
    }
  }
  if (ollamaUrlInput) ollamaUrlInput.value = getOllamaUrl();
}

async function loadOllamaConfig() {
  try {
    const cfg = await api("/api/ollama/config");
    defaultOllamaUrl = cfg.default_url || defaultOllamaUrl;
    if (!ollamaBaseUrl) setOllamaUrl(defaultOllamaUrl, false);
    else if (ollamaUrlInput) ollamaUrlInput.value = getOllamaUrl();
  } catch {
    if (ollamaUrlInput && !ollamaUrlInput.value) ollamaUrlInput.value = getOllamaUrl();
  }
}

function setOllamaSettingsStatus(msg, ok) {
  if (!ollamaSettingsStatus) return;
  ollamaSettingsStatus.textContent = msg;
  ollamaSettingsStatus.className = "settings-status" + (ok === true ? " ok" : ok === false ? " err" : "");
}

async function testOllamaConnection(url) {
  const testUrl = normalizeClientOllamaUrl(url) || defaultOllamaUrl;
  setOllamaSettingsStatus("Testing connection…", null);
  try {
    const res = await fetch(API + "/api/health", {
      headers: { "X-Ollama-Url": testUrl },
    });
    const h = await res.json();
    if (h.ollama?.ok) {
      const n = h.ollama.models?.length || 0;
      setOllamaSettingsStatus(`Connected — ${n} model(s) at ${h.ollama.url}`, true);
      return true;
    }
    setOllamaSettingsStatus(h.ollama?.error || "Connection failed", false);
    return false;
  } catch (e) {
    setOllamaSettingsStatus(`Connection failed: ${e.message}`, false);
    return false;
  }
}

function openOllamaSettings() {
  if (!ollamaDialog) return;
  ollamaUrlInput.value = getOllamaUrl();
  setOllamaSettingsStatus("", null);
  ollamaDialog.showModal();
}

function initOllamaSettings() {
  $("#btn-ollama-settings")?.addEventListener("click", openOllamaSettings);
  $("#btn-ollama-test")?.addEventListener("click", () => testOllamaConnection(ollamaUrlInput.value));
  $("#btn-ollama-reset")?.addEventListener("click", () => {
    setOllamaUrl(defaultOllamaUrl, true);
    setOllamaSettingsStatus(`Reset to server default: ${defaultOllamaUrl}`, true);
  });
  $("#ollama-settings-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = normalizeClientOllamaUrl(ollamaUrlInput.value);
    if (!url) {
      setOllamaSettingsStatus("Enter a valid URL", false);
      return;
    }
    const ok = await testOllamaConnection(url);
    if (!ok) return;
    setOllamaUrl(url, true);
    ollamaDialog.close();
    await checkHealth();
    addChatMsg("system", `Ollama URL updated to ${url}`, {}, false);
  });
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    ...opts,
    headers: { ...apiHeaders(!opts.body || typeof opts.body === "string"), ...opts.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

function setSession(id, filename) {
  sessionId = id;
  if (id) sessionStorage.setItem("maintenanceSessionId", id);
  else sessionStorage.removeItem("maintenanceSessionId");
  sourceBadge.textContent = filename || "X.md (default)";
}

function scheduleSaveReport() {
  clearTimeout(saveReportTimer);
  saveReportTimer = setTimeout(saveReportToStorage, 400);
}

function buildReportSnapshot() {
  return {
    version: STORAGE_VERSION,
    savedAt: new Date().toISOString(),
    sessionId,
    sourceFile: currentSummary?.source_file || sourceBadge?.textContent || "",
    viewMode,
    mdPreviewId: mdPreviewSelect?.value || "",
    summary: currentSummary,
    summaryMarkdown,
    reportBlocks: reportBlocks.map((b) => ({ ...b })),
    chatHistory: chatHistory.map((m) => ({ ...m })),
  };
}

function trimPlotsForStorage(blocks) {
  return blocks.map((b) =>
    b.type === "plot" ? { ...b, image_base64: undefined, _plotStored: !!b.image_base64 } : b
  );
}

function saveReportToStorage() {
  if (!currentSummary && !reportBlocks.length && viewMode !== "preview") return;

  const snapshot = buildReportSnapshot();
  try {
    localStorage.setItem(REPORT_STORAGE_KEY, JSON.stringify(snapshot));
    flashSavedIndicator();
  } catch (e) {
    console.warn("Could not save report to localStorage:", e);
    try {
      snapshot.reportBlocks = trimPlotsForStorage(snapshot.reportBlocks);
      localStorage.setItem(REPORT_STORAGE_KEY, JSON.stringify(snapshot));
    } catch (e2) {
      console.warn("Report save failed after trimming plots:", e2);
    }
  }

  if (currentSummary && viewMode === "live") {
    archiveReportSnapshot(snapshot);
  }
}

function archiveReportSnapshot(snapshot) {
  try {
    const history = loadReportHistory();
    const entry = {
      id: snapshot.savedAt,
      savedAt: snapshot.savedAt,
      sourceFile: snapshot.sourceFile,
      period: snapshot.summary?.period || "",
      months: snapshot.summary?.months || 0,
      blockCount: snapshot.reportBlocks.length,
      summaryMarkdown: snapshot.summaryMarkdown,
      reportBlocks: snapshot.reportBlocks,
      summary: snapshot.summary,
    };
    const dup = history[0];
    if (
      dup &&
      dup.sourceFile === entry.sourceFile &&
      dup.blockCount === entry.blockCount &&
      dup.summaryMarkdown === entry.summaryMarkdown
    ) {
      return;
    }
    history.unshift(entry);
    while (history.length > MAX_HISTORY) history.pop();
    localStorage.setItem(REPORT_HISTORY_KEY, JSON.stringify(history));
  } catch (e) {
    if (e.name === "QuotaExceededError") {
      try {
        const history = loadReportHistory();
        const slim = history.map((h) => ({
          ...h,
          reportBlocks: trimPlotsForStorage(h.reportBlocks || []),
        }));
        while (slim.length > 5) slim.pop();
        localStorage.setItem(REPORT_HISTORY_KEY, JSON.stringify(slim));
      } catch (e2) {
        console.warn("Could not archive report history:", e2);
      }
    }
  }
}

function loadReportHistory() {
  try {
    const raw = localStorage.getItem(REPORT_HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveChatToStorage() {
  try {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(chatHistory.slice(-80)));
  } catch (e) {
    console.warn("Could not save chat history:", e);
  }
}

function restoreChatFromStorage() {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return false;
    chatHistory = JSON.parse(raw);
    chatEl.innerHTML = "";
    chatHistory.forEach((m) => addChatMsg(m.role, m.content, {}, false));
    return chatHistory.length > 0;
  } catch {
    return false;
  }
}

function restoreReportFromStorage() {
  try {
    const raw = localStorage.getItem(REPORT_STORAGE_KEY);
    if (!raw) return false;
    const data = JSON.parse(raw);
    if (data.version !== STORAGE_VERSION || !data.summary) return false;

    currentSummary = data.summary;
    summaryMarkdown = data.summaryMarkdown || data.summary.markdown || "";
    reportBlocks = data.reportBlocks || [];
    if (data.sessionId) {
      sessionId = data.sessionId;
      sessionStorage.setItem("maintenanceSessionId", data.sessionId);
    }

    if (data.mdPreviewId && mdPreviewSelect) {
      mdPreviewSelect.value = data.mdPreviewId;
      if (data.viewMode === "preview" && data.mdPreviewId) {
        showMdPreview(data.mdPreviewId);
        return true;
      }
    }

    viewMode = "live";
    if (mdPreviewSelect) mdPreviewSelect.value = "";
    renderSummary(currentSummary);
    setSession(sessionId, currentSummary.source_file);
    restoredFromStorage = true;
    return true;
  } catch (e) {
    console.warn("Could not restore report from localStorage:", e);
    return false;
  }
}

function flashSavedIndicator() {
  if (!sourceBadge) return;
  const prev = sourceBadge.textContent;
  sourceBadge.textContent = "Saved locally";
  sourceBadge.classList.add("ok");
  setTimeout(() => {
    if (currentSummary?.source_file) {
      sourceBadge.textContent = currentSummary.source_file;
    } else {
      sourceBadge.textContent = prev;
    }
    sourceBadge.classList.remove("ok");
  }, 1200);
}

function clearStoredReport() {
  localStorage.removeItem(REPORT_STORAGE_KEY);
  localStorage.removeItem(CHAT_STORAGE_KEY);
}

async function checkHealth() {
  try {
    const h = await api("/api/health");
    if (h.default_ollama_url) defaultOllamaUrl = h.default_ollama_url;
    const ollamaOk = h.ollama?.ok;
    const models = h.ollama?.models || [];
    const activeUrl = h.ollama?.url || getOllamaUrl();
    statusBadge.textContent = ollamaOk
      ? `Ollama · ${models.length} model(s)`
      : `Ollama offline`;
    statusBadge.title = activeUrl;
    statusBadge.className = "badge " + (ollamaOk ? "ok" : "warn");

    if (h.session?.filename) {
      sourceBadge.textContent = h.session.filename;
    }

    modelSelect.innerHTML = "";
    if (models.length) {
      models.forEach((m) => {
        const opt = document.createElement("option");
        opt.value = m;
        opt.textContent = m;
        modelSelect.appendChild(opt);
      });
    } else {
      modelSelect.innerHTML = '<option value="">No models</option>';
    }
    return h;
  } catch (e) {
    statusBadge.textContent = "Server error";
    statusBadge.className = "badge err";
    return null;
  }
}

function renderSummary(summary) {
  currentSummary = JSON.parse(JSON.stringify(summary));
  summaryMarkdown = summary.markdown;
  const catRows = summary.top_categories
    .map((c) => `<tr><td>${c.name}</td><td>${formatINR(c.amount)}</td><td>${c.pct}%</td></tr>`)
    .join("");

  reportEl.innerHTML = `
    <div class="summary-card" id="summary-block">
      <h3>${summary.title}</h3>
      <p class="source-tag">Source: <strong>${summary.source_file || "ledger"}</strong> · ${summary.period} · ${summary.months} months</p>
      <div class="metrics-grid">
        <div class="metric"><div class="val">${formatINR(summary.avg_monthly_income)}</div><div class="lbl">Avg collections/mo</div></div>
        <div class="metric"><div class="val">${formatINR(summary.avg_monthly_expense)}</div><div class="lbl">Avg expenses/mo</div></div>
        <div class="metric"><div class="val">${formatINR(summary.total_spend)}</div><div class="lbl">Total spend</div></div>
        <div class="metric"><div class="val">${formatINR(summary.latest_balance)}</div><div class="lbl">Latest balance</div></div>
        <div class="metric"><div class="val">${summary.deficit_months}</div><div class="lbl">Deficit months</div></div>
      </div>
      <h4 style="margin:16px 0 8px">Top Categories</h4>
      <table style="width:100%;border-collapse:collapse;font-size:0.9rem">
        <thead><tr style="background:#e8eef4"><th style="padding:6px;text-align:left">Category</th><th style="padding:6px;text-align:right">Amount</th><th style="padding:6px;text-align:right">Share</th></tr></thead>
        <tbody>${catRows}</tbody>
      </table>
      <h4 style="margin:16px 0 8px">Observations</h4>
      <ul class="obs-list" id="obs-list">${summary.observations.map((o) => `<li>${o}</li>`).join("")}</ul>
    </div>
    <div id="report-blocks"></div>
  `;
  renderReportBlocks();
  scheduleSaveReport();
}

function renderReportBlocks() {
  const container = document.getElementById("report-blocks");
  if (!container) return;
  container.innerHTML = reportBlocks
    .map((b, i) => {
      if (b.type === "plot") {
        return `<div class="report-block" data-idx="${i}">
          <h4>${escapeHtml(b.title)}</h4>
          <img src="data:image/png;base64,${b.image_base64}" alt="chart">
          <p class="caption">${escapeHtml(b.caption || "")}</p>
          <div class="block-actions"><button class="btn small secondary" data-remove="${i}">Remove</button></div>
        </div>`;
      }
      return `<div class="report-block" data-idx="${i}">
        ${b.title ? `<h4>${escapeHtml(b.title)}</h4>` : ""}
        <div class="block-body">${escapeHtml(b.content)}</div>
        <div class="block-actions"><button class="btn small secondary" data-remove="${i}">Remove</button></div>
      </div>`;
    })
    .join("");

  container.querySelectorAll("[data-remove]").forEach((btn) => {
    btn.onclick = () => {
      reportBlocks.splice(Number(btn.dataset.remove), 1);
      renderReportBlocks();
      scheduleSaveReport();
    };
  });
  scheduleSaveReport();
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function addTextToReport(title, content) {
  reportBlocks.push({ type: "text", title: title || "", content });
  renderReportBlocks();
  scheduleSaveReport();
  reportEl.scrollTop = reportEl.scrollHeight;
}

function addPlotToReport(plot) {
  reportBlocks.push({
    type: "plot",
    title: plot.title,
    caption: plot.caption,
    image_base64: plot.image_base64,
    spec: plot.spec,
  });
  renderReportBlocks();
  scheduleSaveReport();
  reportEl.scrollTop = reportEl.scrollHeight;
}

function addObservationToReport(content) {
  const list = document.getElementById("obs-list");
  if (list) {
    const li = document.createElement("li");
    li.textContent = content;
    list.appendChild(li);
    summaryMarkdown += `\n- ${content}`;
    if (currentSummary) {
      currentSummary.observations = currentSummary.observations || [];
      currentSummary.observations.push(content);
    }
  } else {
    addTextToReport("Observation", content);
  }
  scheduleSaveReport();
}

function applyReportUpdates(updates) {
  if (!updates?.length) return Promise.resolve();
  ensureLiveReportView();
  updates.forEach((u) => applyOneReportUpdate(u));
  scheduleSaveReport();
  return Promise.resolve();
}

function ensureLiveReportView() {
  if (viewMode !== "preview") return;
  mdPreviewSelect.value = "";
  viewMode = "live";
  if (!currentSummary) return;
  renderSummary({ ...currentSummary, markdown: summaryMarkdown || currentSummary.markdown });
}

function buildExportPayload() {
  return {
    title: currentSummary?.title || "Maintenance Fund Report",
    summary_markdown: summaryMarkdown,
    blocks: reportBlocks.map((b) => ({ ...b })),
    source_file: currentSummary?.source_file || "",
    period: currentSummary?.period || "",
  };
}

function applyOneReportUpdate(u) {
  switch (u.action) {
    case "add_section":
      addTextToReport(u.title || "Analysis", u.content || "");
      break;
    case "add_observation":
      addObservationToReport(u.content || "");
      break;
    case "add_text":
      addTextToReport("", u.content || "");
      break;
    default:
      if (u.content) addTextToReport(u.title || "", u.content);
  }
}

function addChatMsg(role, content, extras = {}, persist = true) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = content;

  if (extras.plot) {
    const plotDiv = document.createElement("div");
    plotDiv.className = "msg-plot";
    plotDiv.innerHTML = `
      <img src="data:image/png;base64,${extras.plot.image_base64}" alt="${escapeHtml(extras.plot.title)}">
      <div class="plot-footer">
        <span>${escapeHtml(extras.plot.title)}</span>
        <button class="btn small primary" type="button">Add to Report</button>
      </div>`;
    plotDiv.querySelector("button").onclick = () => addPlotToReport(extras.plot);
    div.appendChild(plotDiv);
  }

  if (role === "assistant" && content) {
    const actions = document.createElement("div");
    actions.className = "msg-actions";
    const addBtn = document.createElement("button");
    addBtn.className = "btn small secondary";
    addBtn.type = "button";
    addBtn.textContent = "Add reply to Report";
    addBtn.onclick = () => addTextToReport("AI Analysis", content);
    actions.appendChild(addBtn);
    div.appendChild(actions);
  }

  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  if (persist && role !== "system") saveChatToStorage();
  return div;
}

async function loadMdReportList() {
  if (!mdPreviewSelect) return;
  try {
    const data = await api("/api/reports");
    const current = mdPreviewSelect.value;
    mdPreviewSelect.innerHTML = '<option value="">— Live summary —</option>';
    data.reports.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.id;
      opt.textContent = r.path;
      mdPreviewSelect.appendChild(opt);
    });
    if (current && [...mdPreviewSelect.options].some((o) => o.value === current)) {
      mdPreviewSelect.value = current;
    }
  } catch (e) {
    console.warn("Could not load markdown report list:", e);
  }
}

async function showMdPreview(reportId) {
  if (!reportId) {
    viewMode = "live";
    if (restoredFromStorage && currentSummary) {
      renderSummary(currentSummary);
      return;
    }
    await loadSummary(false);
    return;
  }
  viewMode = "preview";
  reportEl.innerHTML = '<div class="upload-progress">Rendering markdown preview…</div>';
  try {
    const data = await api(`/api/reports/preview?report_id=${encodeURIComponent(reportId)}`);
    reportEl.innerHTML = `<div class="md-preview">${data.html}</div>`;
    sourceBadge.textContent = `Preview: ${data.name}`;
    scheduleSaveReport();
  } catch (e) {
    reportEl.innerHTML = `<p style="color:var(--danger)">Preview failed: ${escapeHtml(e.message)}</p>`;
  }
}

async function loadSummary(clearStorage = true) {
  viewMode = "live";
  restoredFromStorage = false;
  if (mdPreviewSelect) mdPreviewSelect.value = "";
  if (clearStorage) {
    reportBlocks = [];
    clearStoredReport();
  }
  $("#btn-load-summary").disabled = true;
  try {
    const summary = await api("/api/summary");
    renderSummary(summary);
    setSession(sessionId, summary.source_file);
    if (!restoredFromStorage) {
      addChatMsg("system", `Report loaded from ${summary.source_file}. Ask me to analyze, plot, or update the report.`);
    }
  } catch (e) {
    reportEl.innerHTML = `<p style="color:var(--danger)">Failed to load: ${e.message}</p>`;
  } finally {
    $("#btn-load-summary").disabled = false;
  }
}

async function uploadFile(file) {
  if (!file) return;
  reportEl.innerHTML = `<div class="upload-progress">Parsing ${escapeHtml(file.name)}…</div>`;
  const form = new FormData();
  form.append("file", file);

  try {
    const res = await fetch(API + "/api/upload", { method: "POST", body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    setSession(data.session_id, data.filename);
    chatHistory = [];
    clearStoredReport();
    reportBlocks = [];
    restoredFromStorage = false;
    renderSummary(data.summary);
    addChatMsg("system", `Uploaded ${data.filename}: ${data.months} months (${data.date_range}). Report generated.`);
    await loadMdReportList();
    await checkHealth();
  } catch (e) {
    reportEl.innerHTML = `<p style="color:var(--danger)">Upload failed: ${escapeHtml(e.message)}</p>`;
  }
  $("#file-upload").value = "";
}

async function sendChat(text) {
  if (!text.trim()) return;
  const btn = $("#btn-send");
  btn.disabled = true;
  addChatMsg("user", text);
  chatHistory.push({ role: "user", content: text });
  $("#chat-input").value = "";

  const typing = document.createElement("div");
  typing.className = "typing";
  typing.textContent = "Thinking…";
  chatEl.appendChild(typing);

  try {
    const res = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        messages: chatHistory,
        model: modelSelect.value || undefined,
        generate_plot: $("#auto-plot").checked,
        report_summary: summaryMarkdown.slice(0, 3000),
      }),
    });
    typing.remove();
    addChatMsg("assistant", res.reply, { plot: res.plot });
    chatHistory.push({ role: "assistant", content: res.reply });

    const autoAdd = $("#auto-plot").checked;

    if (res.report_updates?.length) {
      await applyReportUpdates(res.report_updates);
      addChatMsg("system", `Applied ${res.report_updates.length} update(s) to the report.`);
    }

    if (res.plot) {
      if (autoAdd) {
        addPlotToReport(res.plot);
        addChatMsg("system", "Chart added to the report.");
      } else {
        addChatMsg("system", "Chart generated — click Add to Report to include it.");
      }
    } else if (autoAdd && !res.report_updates?.length && res.reply?.trim()) {
      const askedForReport = /\b(report|add to the|update the|section|observation|include in)\b/i.test(text);
      if (askedForReport) {
        addTextToReport("AI Analysis", res.reply);
        addChatMsg("system", "Added AI response to the report.");
      }
    }

    saveChatToStorage();
    scheduleSaveReport();
  } catch (e) {
    typing.remove();
    addChatMsg("assistant", `Error: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

async function exportReport() {
  try {
    ensureLiveReportView();
    if (!currentSummary && !reportBlocks.length) {
      alert("Load or generate a report first.");
      return;
    }
    saveReportToStorage();
    const html = await api("/api/export/html", {
      method: "POST",
      body: JSON.stringify(buildExportPayload()),
    });
    const blob = new Blob([html], { type: "text/html" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "maintenance_report.html";
    a.click();
  } catch (e) {
    alert("Export failed: " + e.message);
  }
}

async function exportCleanedData() {
  const format = $("#data-export-format")?.value || "json";
  const btn = $("#btn-export-data");
  if (btn) btn.disabled = true;
  try {
    const res = await fetch(`${API}/api/export/data?format=${encodeURIComponent(format)}`, {
      headers: apiHeaders(false),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const blob = await res.blob();
    const cd = res.headers.get("content-disposition") || "";
    const match = cd.match(/filename="([^"]+)"/);
    const filename = match?.[1] || `cleaned_data.${format}`;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
  } catch (e) {
    alert("Data export failed: " + e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function showDocumentPreview(title, html) {
  if (!docPreviewDialog || !docPreviewBody) return;
  docPreviewTitle.textContent = title || "Document Preview";
  docPreviewBody.innerHTML = `<div class="md-preview">${html}</div>`;
  docPreviewDialog.showModal();
}

async function previewDocument() {
  const btn = $("#btn-preview-doc");
  if (btn) btn.disabled = true;
  try {
    const mdId = mdPreviewSelect?.value;
    if (mdId) {
      const data = await api(`/api/reports/preview?report_id=${encodeURIComponent(mdId)}`);
      showDocumentPreview(data.name || mdId, data.html);
      return;
    }
    ensureLiveReportView();
    if (!currentSummary) {
      alert("Load or generate a report first, or pick a .md file from the dropdown.");
      return;
    }
    const data = await api("/api/reports/preview-live", {
      method: "POST",
      body: JSON.stringify(buildExportPayload()),
    });
    showDocumentPreview(data.title, data.html);
  } catch (e) {
    alert("Preview failed: " + e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function initDocumentPreview() {
  $("#btn-preview-doc")?.addEventListener("click", previewDocument);
  $("#btn-doc-preview-close")?.addEventListener("click", () => docPreviewDialog?.close());
  $("#btn-doc-preview-print")?.addEventListener("click", () => {
    const w = window.open("", "_blank");
    if (!w) return;
    w.document.write(`<!DOCTYPE html><html><head><title>${docPreviewTitle.textContent}</title>
      <style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.55}
      h1,h2,h3{color:#1e3a5f} table{border-collapse:collapse;width:100%} th,td{border:1px solid #bbb;padding:5px 8px}
      img{max-width:100%}</style></head><body>${docPreviewBody.innerHTML}</body></html>`);
    w.document.close();
    w.focus();
    w.print();
  });
}

/* Resizable split pane */
function initResizer() {
  const resizer = $("#resizer");
  const chatPanel = $("#chat-panel");
  const layout = $("#layout");
  if (!resizer || window.innerWidth <= 768) return;

  const saved = localStorage.getItem("chatPanelWidth");
  if (saved) {
    chatPanel.style.flexBasis = saved;
    chatPanel.style.width = saved;
    document.documentElement.style.setProperty("--chat-width", saved);
  }

  let startX, startWidth;

  resizer.addEventListener("mousedown", (e) => {
    e.preventDefault();
    startX = e.clientX;
    startWidth = chatPanel.getBoundingClientRect().width;
    resizer.classList.add("dragging");
    document.body.classList.add("resizing");

    const onMove = (ev) => {
      const dx = startX - ev.clientX;
      const newW = Math.min(window.innerWidth * 0.7, Math.max(280, startWidth + dx));
      const w = `${newW}px`;
      chatPanel.style.flexBasis = w;
      chatPanel.style.width = w;
      document.documentElement.style.setProperty("--chat-width", w);
    };

    const onUp = () => {
      resizer.classList.remove("dragging");
      document.body.classList.remove("resizing");
      localStorage.setItem("chatPanelWidth", chatPanel.style.width);
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

$("#btn-load-summary").onclick = () => loadSummary(true);
$("#btn-reload").onclick = async () => {
  sessionId = null;
  sessionStorage.removeItem("maintenanceSessionId");
  clearStoredReport();
  restoredFromStorage = false;
  chatHistory = [];
  chatEl.innerHTML = "";
  await api("/api/data?refresh=true");
  reportBlocks = [];
  await loadSummary(false);
};
$("#btn-export").onclick = exportReport;
$("#btn-export-data")?.addEventListener("click", exportCleanedData);
$("#file-upload").onchange = (e) => uploadFile(e.target.files[0]);
if (mdPreviewSelect) {
  mdPreviewSelect.onchange = () => showMdPreview(mdPreviewSelect.value);
}

$("#chat-form").onsubmit = (e) => {
  e.preventDefault();
  sendChat($("#chat-input").value);
};

document.querySelectorAll(".chip").forEach((chip) => {
  chip.onclick = () => {
    $("#chat-input").value = chip.dataset.prompt;
    $("#chat-input").focus();
  };
});

initResizer();
initOllamaSettings();
initDocumentPreview();

window.addEventListener("beforeunload", () => {
  clearTimeout(saveReportTimer);
  saveReportToStorage();
});

loadOllamaConfig()
  .then(() => checkHealth())
  .then(async () => {
  await loadMdReportList();
  const hadChat = restoreChatFromStorage();
  const hadReport = restoreReportFromStorage();
  if (!hadReport) {
    await loadSummary(false);
  } else {
    addChatMsg(
      "system",
      `Restored your last report from browser storage (${currentSummary?.source_file || "saved"}).`,
      {},
      false
    );
  }
  if (!hadChat && !hadReport) {
    addChatMsg(
      "system",
      "Welcome! Upload an expense sheet, preview any .md report from the dropdown, or use the live summary. Reports are saved automatically in your browser.",
      {},
      false
    );
  }
});
