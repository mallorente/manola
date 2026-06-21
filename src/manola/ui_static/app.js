const state = {
  data: null,
  view: "archive",
  selectedPath: null,
  tab: "overview",
  filter: "all",
  query: "",
  lang: localStorage.getItem("manola.appLanguage") || "en",
  theme: localStorage.getItem("manola.theme") || "light",
  highlight: localStorage.getItem("manola.highlightColor") || "#3a6ae0",
  sortKey: localStorage.getItem("manola.sortKey") || "date",
  sortDir: localStorage.getItem("manola.sortDir") || "desc",
  recordingJobId: null,
};

const MEETING_TYPES = [
  "general", "sales_discovery", "sales_demo", "customer_success", "client_update",
  "internal_sync", "one_on_one", "job_interview", "case_interview", "project_review",
  "incident_postmortem", "brainstorm", "strategy", "workshop", "refinement",
  "daily", "retro", "planning",
];
const SHARE_POLICIES = ["private", "report", "report_transcript", "all"];

const I18N = {
  en: {
    recordMeeting: "Record meeting",
    library: "Library",
    allMeetings: "All meetings",
    needsAttention: "Needs attention",
    importAudio: "Import audio",
    system: "System",
    devices: "Devices",
    doctor: "Doctor",
    settings: "Settings",
    toggleTheme: "Toggle theme",
    localWorkspace: "Local workspace",
    meetings: "Meetings",
    searchMeetings: "Search meetings...",
    all: "All",
    ready: "Ready",
    sortBy: "Sort by",
    sortDate: "Date",
    sortTitle: "Title",
    sortType: "Type",
    sortDuration: "Duration",
    sortAsc: "Asc",
    sortDesc: "Desc",
    overview: "Overview",
    transcript: "Transcript",
    report: "Report",
    audio: "Audio",
    metadata: "Metadata",
    general: "General",
    generalSub: "Application preferences stored in this browser.",
    backendConfig: "Manola config",
    backendConfigSub: "Read-only values loaded from the local backend config.",
    appLanguage: "App language",
    appLanguageSub: "Changes interface labels only.",
    highlightColor: "Highlight color",
    highlightColorSub: "Used for primary actions and active states.",
    reset: "Reset",
    archive: "Archive",
    transcription: "Transcription",
    reports: "Reports",
    sharing: "Sharing",
    prompts: "Prompts",
    advanced: "Advanced",
    transcriptLanguage: "Transcript language",
    defaultLlmProfile: "Default LLM profile",
    generateReports: "Generate reports automatically",
    workspaceDir: "Local archive path",
    sharedDir: "Shared export path",
    model: "Model",
    device: "Device",
    computeType: "Compute type",
    doctorSub: "Dependency and configuration checks from Manola.",
    devicesSub: "Detected microphones and system audio devices.",
    importSub: "Import UI is designed; processing needs a backend job API.",
    backendGap: "Backend gap",
    unavailable: "Unavailable in this UI",
    copyCommand: "Copy CLI command",
    regenerateReport: "Regenerate report",
    retranscribe: "Retranscribe",
    jobStarting: "Starting…",
    jobRunning: "Running…",
    jobDone: "Done",
    jobFailed: "Failed",
    jobRetry: "Try again",
    privacyConfirm: "This sends the meeting transcript to the configured remote LLM. Continue?",
    actions: "Actions",
    sharePolicy: "Share policy",
    policyReport: "Report only",
    policyReportTranscript: "Report + transcript",
    policyAll: "Everything (incl. audio)",
    export: "Export",
    apply: "Apply",
    reject: "Reject",
    save: "Save",
    saved: "Saved",
    saveFailed: "Save failed",
    saveDevices: "Save devices",
    microphone: "Microphone",
    speakerLoopback: "Speaker / loopback",
    systemDefault: "System default",
    notConfigured: "Not configured",
    recordSub: "Record a meeting from the browser. Capture starts on the server.",
    recordLiveLater: "Live level meters and live transcript arrive in a later step.",
    recordReportNote: "Stopping saves the meeting and transcribes it. Generate the report from the meeting afterwards.",
    allowPartial: "Allow partial capture",
    allowPartialSub: "Keep the recording even if one channel is silent (e.g. in-person, no system audio). Uncheck to require both mic and system audio.",
    recordPreviewEmpty: "Live preview transcript appears here while recording. The final transcript is generated when you stop.",
    lowConfidenceConfirm: "This suggestion looks low confidence. Apply anyway?",
    noReport: "No report generated yet.",
    noReportSub: "Use `uv run manola summarize <meeting-id-or-path>` from the CLI until the UI has an async report job API.",
    noTranscript: "No transcript generated yet.",
    noTranscriptSub: "Use `uv run manola transcribe <meeting-id-or-path>` from the CLI until the UI has an async transcription job API.",
    repairAudio: "Repair audio",
    sourceAudio: "Source audio",
    normalizedAudio: "Normalized audio",
    missingAudio: "Expected audio artifact is missing.",
    runCli: "Run in CLI",
    startRecording: "Start recording",
    stopRecording: "Stop recording",
    processRecording: "Process recording",
    chooseAudio: "Choose audio",
    processImport: "Process import",
    exportMeeting: "Export",
    enrichMetadata: "Enrich metadata",
    liveTranscript: "Live transcript",
    testDevices: "Test devices",
    rerunDoctor: "Rerun doctor",
    saveMetadata: "Save metadata",
    applySuggestions: "Apply suggestions",
    metadataReadonly: "Metadata editing is read-only until write endpoints exist.",
    noSuggestions: "No metadata suggestions found.",
    reportStale: "Report may be outdated. Transcript changed after this report.",
    noMeeting: "Select a meeting to inspect transcript, report, audio, and metadata.",
    noMeetings: "No meetings found.",
    healthOk: "Ready",
    healthWarn: "Needs attention",
  },
  es: {
    recordMeeting: "Grabar reunión",
    library: "Biblioteca",
    allMeetings: "Todas las reuniones",
    needsAttention: "Requiere atención",
    importAudio: "Importar audio",
    system: "Sistema",
    devices: "Dispositivos",
    doctor: "Doctor",
    settings: "Configuración",
    toggleTheme: "Cambiar tema",
    localWorkspace: "Espacio local",
    meetings: "Reuniones",
    searchMeetings: "Buscar reuniones...",
    all: "Todas",
    ready: "Listas",
    sortBy: "Ordenar por",
    sortDate: "Fecha",
    sortTitle: "Título",
    sortType: "Tipo",
    sortDuration: "Duración",
    sortAsc: "Asc",
    sortDesc: "Desc",
    overview: "Resumen",
    transcript: "Transcripción",
    report: "Informe",
    audio: "Audio",
    metadata: "Metadatos",
    general: "General",
    generalSub: "Preferencias de la aplicación guardadas en este navegador.",
    backendConfig: "Configuracion de Manola",
    backendConfigSub: "Valores de solo lectura cargados desde la configuracion local.",
    appLanguage: "Idioma de la aplicación",
    appLanguageSub: "Solo cambia las etiquetas de la interfaz.",
    highlightColor: "Color de énfasis",
    highlightColorSub: "Se usa en acciones primarias y estados activos.",
    reset: "Restablecer",
    archive: "Archivo",
    transcription: "Transcripción",
    reports: "Informes",
    sharing: "Compartir",
    prompts: "Prompts",
    advanced: "Avanzado",
    transcriptLanguage: "Idioma de transcripción",
    defaultLlmProfile: "Perfil LLM por defecto",
    generateReports: "Generar informes automáticamente",
    workspaceDir: "Ruta del archivo local",
    sharedDir: "Ruta de exportación compartida",
    model: "Modelo",
    device: "Dispositivo",
    computeType: "Tipo de cómputo",
    doctorSub: "Comprobaciones de dependencias y configuración de Manola.",
    devicesSub: "Micrófonos y dispositivos de audio detectados.",
    importSub: "La UI de importación está diseñada; procesar requiere una API de trabajos backend.",
    backendGap: "Gap de backend",
    unavailable: "No disponible en esta UI",
    copyCommand: "Copiar comando CLI",
    regenerateReport: "Regenerar informe",
    retranscribe: "Retranscribir",
    jobStarting: "Iniciando…",
    jobRunning: "En curso…",
    jobDone: "Hecho",
    jobFailed: "Fallo",
    jobRetry: "Reintentar",
    privacyConfirm: "Esto envía la transcripción de la reunión al LLM remoto configurado. ¿Continuar?",
    actions: "Acciones",
    sharePolicy: "Política de compartición",
    policyReport: "Solo informe",
    policyReportTranscript: "Informe + transcripción",
    policyAll: "Todo (incl. audio)",
    export: "Exportar",
    apply: "Aplicar",
    reject: "Descartar",
    save: "Guardar",
    saved: "Guardado",
    saveFailed: "Error al guardar",
    saveDevices: "Guardar dispositivos",
    microphone: "Micrófono",
    speakerLoopback: "Altavoz / loopback",
    systemDefault: "Predeterminado del sistema",
    notConfigured: "Sin configurar",
    recordSub: "Graba una reunión desde el navegador. La captura ocurre en el servidor.",
    recordLiveLater: "Los medidores de nivel y la transcripción en vivo llegan en un paso posterior.",
    recordReportNote: "Al detener se guarda la reunión y se transcribe. Genera el informe desde la reunión después.",
    allowPartial: "Permitir captura parcial",
    allowPartialSub: "Conserva la grabación aunque un canal esté en silencio (p. ej. presencial, sin audio de sistema). Desmárcalo para exigir micro y audio de sistema.",
    recordPreviewEmpty: "La transcripción en vivo aparece aquí mientras grabas. La transcripción final se genera al detener.",
    lowConfidenceConfirm: "Esta sugerencia parece de baja confianza. ¿Aplicar de todos modos?",
    noReport: "Aun no hay informe generado.",
    noReportSub: "Usa `uv run manola summarize <meeting-id-or-path>` desde la CLI hasta que la interfaz tenga una API asincrona para informes.",
    noTranscript: "Aun no hay transcripcion generada.",
    noTranscriptSub: "Usa `uv run manola transcribe <meeting-id-or-path>` desde la CLI hasta que la interfaz tenga una API asincrona de transcripcion.",
    repairAudio: "Reparar audio",
    sourceAudio: "Audio fuente",
    normalizedAudio: "Audio normalizado",
    missingAudio: "Falta un artefacto de audio esperado.",
    runCli: "Ejecutar en CLI",
    startRecording: "Iniciar grabacion",
    stopRecording: "Detener grabacion",
    processRecording: "Procesar grabacion",
    chooseAudio: "Elegir audio",
    processImport: "Procesar importacion",
    exportMeeting: "Exportar",
    enrichMetadata: "Enriquecer metadatos",
    liveTranscript: "Transcripcion en vivo",
    testDevices: "Probar dispositivos",
    rerunDoctor: "Reejecutar doctor",
    saveMetadata: "Guardar metadatos",
    applySuggestions: "Aplicar sugerencias",
    metadataReadonly: "La edicion de metadatos es de solo lectura hasta que existan endpoints de escritura.",
    noSuggestions: "No hay sugerencias de metadatos.",
    reportStale: "El informe puede estar obsoleto. La transcripción cambió después del informe.",
    noMeeting: "Selecciona una reunión para inspeccionar transcripción, informe, audio y metadatos.",
    noMeetings: "No se encontraron reuniones.",
    healthOk: "Lista",
    healthWarn: "Requiere atención",
  },
};

const t = (key) => (I18N[state.lang] || I18N.en)[key] || I18N.en[key] || key;

function applyPrefs() {
  document.documentElement.lang = state.lang;
  document.getElementById("app").dataset.theme = state.theme;
  document.documentElement.style.setProperty("--accent", state.highlight);
  document.documentElement.style.setProperty("--accent-bg", mixHex(state.highlight, state.theme === "dark" ? "#1f1b18" : "#ffffff", 0.88));
  document.documentElement.style.setProperty("--accent-border", mixHex(state.highlight, state.theme === "dark" ? "#1f1b18" : "#ffffff", 0.72));
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
}

function mixHex(a, b, weightB) {
  const ah = a.replace("#", "");
  const bh = b.replace("#", "");
  const ar = parseInt(ah.slice(0, 2), 16);
  const ag = parseInt(ah.slice(2, 4), 16);
  const ab = parseInt(ah.slice(4, 6), 16);
  const br = parseInt(bh.slice(0, 2), 16);
  const bg = parseInt(bh.slice(2, 4), 16);
  const bb = parseInt(bh.slice(4, 6), 16);
  const w = weightB;
  const h = (n) => Math.round(n).toString(16).padStart(2, "0");
  return `#${h(ar * (1 - w) + br * w)}${h(ag * (1 - w) + bg * w)}${h(ab * (1 - w) + bb * w)}`;
}

async function api(path, options) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// --- Reusable async-job component (ADR-0003) --------------------------------
// runJob() is the single entry point every long-running UI action uses: it
// POSTs to /api/jobs/<action>, polls /api/jobs/<id> ~1s, renders the
// running/progress/done/failed state into `mount`, and calls onDone(result) on
// success. Batch 3 actions (regenerate report, enrich, export, repair) reuse
// it; remote-LLM actions pass { confirmRemoteLlm: true } to clear the privacy
// gate. See PR for #31.
async function runJob(action, params, mount, { confirmRemoteLlm = false, onDone } = {}) {
  const body = { ...(params || {}) };
  if (confirmRemoteLlm) body.confirm_remote_llm = true;
  renderJobStatus(mount, { status: "starting" });
  let job;
  try {
    job = await api(`/api/jobs/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    renderJobStatus(mount, { status: "failed", error: err.message });
    return null;
  }
  return pollJob(job.id, mount, onDone);
}

async function pollJob(jobId, mount, onDone) {
  for (;;) {
    let job;
    try {
      job = await api(`/api/jobs/${jobId}`);
    } catch (err) {
      renderJobStatus(mount, { status: "failed", error: err.message });
      return null;
    }
    renderJobStatus(mount, job);
    if (job.status === "done") {
      if (onDone) await onDone(job.result);
      return job;
    }
    if (job.status === "failed") return job;
    await delay(1000);
  }
}

function renderJobStatus(mount, job) {
  if (!mount) return;
  const status = job.status || "starting";
  if (status === "failed") {
    mount.innerHTML = `<span class="job-status failed"><span class="job-dot failed"></span>${t("jobFailed")}: ${escapeHtml(job.error || "")}</span>`;
    return;
  }
  if (status === "done") {
    mount.innerHTML = `<span class="job-status done"><span class="job-dot done"></span>${t("jobDone")}</span>`;
    return;
  }
  const label = status === "running" ? t("jobRunning") : t("jobStarting");
  const step = job.step && status === "running" ? ` · ${escapeHtml(job.step)}` : "";
  mount.innerHTML = `<span class="job-status running"><span class="spinner"></span>${label}${step}</span>`;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Re-fetch a single meeting after a job mutates it, then re-render in place.
async function refreshMeeting(path) {
  const updated = await api(`/api/meeting?path=${encodeURIComponent(path)}`);
  const idx = (state.data?.meetings || []).findIndex((x) => x.path === path);
  if (idx >= 0) state.data.meetings[idx] = updated;
  render();
}

async function apiPost(path, body) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
}

// Mirror the CLI's explicit remote-LLM privacy notice before summarize/enrich.
function confirmRemoteLlm() {
  return window.confirm(t("privacyConfirm"));
}

// Generic helper that wires a button to a job via the reusable component.
// Batch 3 actions (regenerate, enrich, export, repair) all go through here.
function wireJobButton(btn, mount, action, params, { needsConfirm = false, onDone } = {}) {
  if (!btn) return;
  btn.addEventListener("click", async () => {
    if (needsConfirm && !confirmRemoteLlm()) return;
    btn.disabled = true;
    await runJob(action, params, mount, { confirmRemoteLlm: needsConfirm, onDone });
    btn.disabled = false;
  });
}

// Tiny inline status for non-job POSTs (config/apply): saved / failed.
function flashStatus(mount, ok, message) {
  if (!mount) return;
  const cls = ok ? "done" : "failed";
  const label = message || (ok ? t("saved") : t("saveFailed"));
  mount.innerHTML = `<span class="job-status ${cls}"><span class="job-dot ${cls}"></span>${escapeHtml(label)}</span>`;
}

async function boot() {
  applyPrefs();
  bindShell();
  state.data = await api("/api/state");
  state.selectedPath = state.data.meetings[0]?.path || null;
  render();
}

function bindShell() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetView = btn.dataset.view;
      if (targetView === "attention") {
        state.view = "archive";
        state.filter = "attention";
      } else {
        state.view = targetView;
        if (targetView === "archive") state.filter = "all";
      }
      render();
    });
  });
  document.getElementById("recordButton").addEventListener("click", () => {
    state.view = "record";
    render();
  });
  document.getElementById("themeToggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    localStorage.setItem("manola.theme", state.theme);
    applyPrefs();
  });
}

function render() {
  applyPrefs();
  document.getElementById("meetingCount").textContent = String(state.data?.meetings.length || 0);
  document.getElementById("attentionCount").textContent = String((state.data?.meetings || []).filter((m) => m.health.level !== "ok").length);
  document.getElementById("workspacePath").textContent = state.data?.config.workspace_dir || "...";
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === activeNavView());
  });

  if (state.view === "archive") renderArchive();
  else if (state.view === "settings") renderSettings();
  else if (state.view === "devices") renderDevices();
  else if (state.view === "doctor") renderDoctor();
  else if (state.view === "import") renderImport();
  else if (state.view === "record") renderRecord();
}

function activeNavView() {
  return state.view === "archive" && state.filter === "attention" ? "attention" : state.view;
}

function cloneTemplate(id) {
  return document.getElementById(id).content.cloneNode(true);
}

function renderArchive() {
  const main = document.getElementById("main");
  main.innerHTML = "";
  main.appendChild(cloneTemplate("archiveTemplate"));
  applyPrefs();

  const meetings = filteredMeetings();
  document.getElementById("archiveSummary").textContent = `${meetings.length} / ${state.data.meetings.length}`;
  const search = document.getElementById("meetingSearch");
  search.value = state.query;
  search.addEventListener("input", () => {
    state.query = search.value;
    drawMeetingList();
  });
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.filter === state.filter);
    chip.addEventListener("click", () => {
      state.filter = chip.dataset.filter;
      renderArchive();
    });
  });
  bindSortControls();
  drawMeetingList();
  renderDetail();
}

function bindSortControls() {
  const sortSelect = document.getElementById("meetingSort");
  if (sortSelect) {
    sortSelect.value = state.sortKey;
    sortSelect.addEventListener("change", () => {
      state.sortKey = sortSelect.value;
      localStorage.setItem("manola.sortKey", state.sortKey);
      drawMeetingList();
    });
  }
  const sortDirButton = document.getElementById("meetingSortDir");
  if (sortDirButton) {
    sortDirButton.textContent = sortDirLabel();
    sortDirButton.addEventListener("click", () => {
      state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      localStorage.setItem("manola.sortDir", state.sortDir);
      sortDirButton.textContent = sortDirLabel();
      drawMeetingList();
    });
  }
}

function sortDirLabel() {
  return state.sortDir === "asc" ? `↑ ${t("sortAsc")}` : `↓ ${t("sortDesc")}`;
}

function sortMeetings(meetings) {
  const direction = state.sortDir === "asc" ? 1 : -1;
  return [...meetings].sort((a, b) => compareMeetings(a, b, state.sortKey) * direction);
}

function compareMeetings(a, b, key) {
  if (key === "title") return meetingTitle(a).localeCompare(meetingTitle(b), undefined, { sensitivity: "base" });
  if (key === "type") return String(a.meeting_type || "").localeCompare(String(b.meeting_type || ""));
  if (key === "duration") return (a.duration_seconds || 0) - (b.duration_seconds || 0);
  return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
}

function filteredMeetings() {
  const q = state.query.toLowerCase().trim();
  return (state.data?.meetings || []).filter((m) => {
    if (state.filter === "attention" && m.health.level === "ok") return false;
    if (state.filter === "ready" && m.health.level !== "ok") return false;
    if (!q) return true;
    return [m.title, m.id, m.project, m.meeting_type, m.language, m.report_excerpt, m.transcript_excerpt].filter(Boolean).join(" ").toLowerCase().includes(q);
  });
}

function drawMeetingList() {
  const list = document.getElementById("meetingList");
  if (!list) return;
  const meetings = sortMeetings(filteredMeetings());
  if (!meetings.length) {
    list.innerHTML = `<div class="empty">${t("noMeetings")}</div>`;
    return;
  }
  list.innerHTML = "";
  groupMeetingsByDay(meetings).forEach((group) => {
    const heading = document.createElement("div");
    heading.className = "meeting-day";
    heading.textContent = group.label;
    list.appendChild(heading);

    group.meetings.forEach((m) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = `meeting-row ${m.path === state.selectedPath ? "selected" : ""}`;
      row.innerHTML = `
        <span class="status-dot ${m.health.level === "ok" ? "ok" : "warn"}"></span>
        <div style="min-width:0;flex:1">
          <div class="meeting-title">${escapeHtml(meetingTitle(m))}</div>
          <div class="meeting-meta">
            <span class="badge type">${escapeHtml(m.meeting_type || "general")}</span>
            <span class="badge share">${escapeHtml(shareLabel(m.share_policy))}</span>
            <span>${formatTime(m.created_at)}</span>
            <span>${escapeHtml(m.language || "auto")}</span>
            <span class="mono" style="margin-left:auto">${m.duration_label || "?"}</span>
          </div>
          ${m.health.level === "ok" ? "" : `<div class="meeting-meta"><span class="badge warn">${escapeHtml(m.health.label)}</span></div>`}
        </div>`;
      row.addEventListener("click", () => {
        state.selectedPath = m.path;
        renderArchive();
      });
      list.appendChild(row);
    });
  });
}

function groupMeetingsByDay(meetings) {
  const groups = new Map();
  meetings.forEach((meeting) => {
    const key = dayKey(meeting.created_at);
    if (!groups.has(key)) groups.set(key, { label: formatDay(meeting.created_at), meetings: [] });
    groups.get(key).meetings.push(meeting);
  });
  return Array.from(groups.values());
}

function meetingTitle(meeting) {
  if (meeting.title) return meeting.title;
  if (meeting.id) return meeting.id.replace(/^\d{4}-\d{2}-\d{2}__/, "").replace(/__/g, " / ").replace(/-/g, " ");
  if (meeting.path) return meeting.path.split(/[\\/]/).filter(Boolean).pop();
  return "Untitled meeting";
}

function shareLabel(policy) {
  return policy ? `share: ${policy}` : "share: private";
}

function renderDetail() {
  const pane = document.getElementById("detailPane");
  const m = state.data.meetings.find((x) => x.path === state.selectedPath);
  if (!m) {
    pane.innerHTML = `<div class="empty">${t("noMeeting")}</div>`;
    return;
  }
  const tabs = ["overview", "transcript", "report", "audio", "metadata"];
  pane.innerHTML = `
    <header class="detail-header">
      <div style="min-width:0">
        <h1 style="margin:0">${escapeHtml(m.title)}</h1>
        <div class="muted mono" style="font-size:12px">${escapeHtml(m.id)}</div>
      </div>
      <div class="tabs" style="margin-left:auto">
        ${tabs.map((tab) => `<button class="tab ${state.tab === tab ? "active" : ""}" data-tab="${tab}" type="button">${t(tab)}</button>`).join("")}
      </div>
    </header>
    <div class="detail-body"><div class="readable" id="tabBody"></div></div>`;
  pane.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.tab = btn.dataset.tab;
      renderDetail();
    });
  });
  const body = document.getElementById("tabBody");
  if (state.tab === "overview") renderOverview(body, m);
  if (state.tab === "transcript") renderTranscript(body, m);
  if (state.tab === "report") renderReport(body, m);
  if (state.tab === "audio") renderAudioTab(body, m);
  if (state.tab === "metadata") renderMetadata(body, m);
}

function renderOverview(body, m) {
  body.innerHTML = `
    ${m.health.level === "ok" ? "" : `<div class="panel warn"><strong>${escapeHtml(m.health.label)}</strong><p>${escapeHtml(m.health.detail)}</p>${gapButton("repairBackend")}</div>`}
    <div class="grid-2">
      ${metric("Status", m.health.level === "ok" ? t("healthOk") : t("healthWarn"))}
      ${metric("Duration", m.duration_label || "?")}
      ${metric(t("transcriptLanguage"), m.language)}
      ${metric("Report type", m.meeting_type)}
    </div>
    <div class="panel">
      <h2>Pipeline</h2>
      ${pipelineRows(m)}
    </div>
    ${actionsPanel(m)}`;
  bindActionsPanel(m);
}

function actionsPanel(m) {
  const policies = ["report", "report_transcript", "all"];
  const labels = { report: t("policyReport"), report_transcript: t("policyReportTranscript"), all: t("policyAll") };
  const current = m.share_policy && m.share_policy !== "private" ? m.share_policy : "report";
  return `<div class="panel">
    <h2>${t("actions")}</h2>
    <div class="metadata-actions">
      <button class="secondary-button" id="ovRetranscribeBtn" type="button">${t("retranscribe")}</button>
      <button class="secondary-button" id="ovRegenerateBtn" type="button">${t("regenerateReport")}</button>
      <button class="secondary-button" id="ovEnrichBtn" type="button">${t("enrichMetadata")}</button>
      <button class="secondary-button" id="ovRepairBtn" type="button">${t("repairAudio")}</button>
    </div>
    <span class="job-mount" id="ovJobStatus"></span>
    <div class="setting-row" style="margin-top:10px">
      <span>${t("sharePolicy")}</span>
      <select id="exportPolicy" class="control sort-select">
        ${policies.map((p) => `<option value="${p}" ${p === current ? "selected" : ""}>${escapeHtml(labels[p])}</option>`).join("")}
      </select>
      <button class="secondary-button" id="exportBtn" type="button">${t("export")}</button>
      <span class="job-mount" id="exportJob"></span>
    </div>
    <p class="setting-sub">Export requires a shared directory configured in Settings.</p>
  </div>`;
}

function bindActionsPanel(m) {
  const status = document.getElementById("ovJobStatus");
  wireJobButton(document.getElementById("ovRetranscribeBtn"), status, "transcribe", { meeting: m.path, force: true }, { onDone: async () => { await refreshMeeting(m.path); } });
  wireJobButton(document.getElementById("ovRegenerateBtn"), status, "summarize", { meeting: m.path, force: true }, { needsConfirm: true, onDone: async () => { await refreshMeeting(m.path); } });
  wireJobButton(document.getElementById("ovEnrichBtn"), status, "enrich", { meeting: m.path, force: true }, { needsConfirm: true, onDone: async () => { await refreshMeeting(m.path); } });
  wireJobButton(document.getElementById("ovRepairBtn"), status, "repair", { meeting: m.path }, { onDone: async () => { await refreshMeeting(m.path); } });

  const exportBtn = document.getElementById("exportBtn");
  const exportMount = document.getElementById("exportJob");
  if (exportBtn) {
    exportBtn.addEventListener("click", async () => {
      const policy = document.getElementById("exportPolicy").value;
      exportBtn.disabled = true;
      await runJob("export", { meeting: m.path, policy }, exportMount, {});
      exportBtn.disabled = false;
    });
  }
}

function renderTranscript(body, m) {
  const lines = parseTranscript(m.transcript_text);
  body.innerHTML = `
    ${m.health.transcript_mismatch ? `<div class="panel warn"><strong>${escapeHtml(m.health.label)}</strong><p>${escapeHtml(m.health.detail)}</p>${gapButton("transcribeBackend")}</div>` : ""}
    <div class="panel report-context">
      <div>
        <strong>transcript.md</strong>
        <div class="meeting-meta">
          <span class="badge ${m.health.transcript_mismatch ? "warn" : "good"}">${m.transcript_end_label || "no timestamps"}</span>
          <span class="badge">${escapeHtml(m.transcription_model || "model unknown")}</span>
          <span class="badge">${escapeHtml(m.transcription_device || "device unknown")}</span>
          <span class="badge">${escapeHtml(m.transcription_compute_type || "compute unknown")}</span>
          <span>${escapeHtml(m.language || "auto")}</span>
        </div>
      </div>
      <div class="action-with-status">
        <button class="secondary-button" id="retranscribeBtn" type="button">${t("retranscribe")}</button>
        <span class="job-mount" id="retranscribeJob"></span>
      </div>
    </div>
    ${m.transcript_text ? (lines.length ? lines.map((line) => `<div class="transcript-line"><div class="timestamp">${escapeHtml(line.time || "")}</div><div>${line.speaker ? `<strong class="speaker">${escapeHtml(line.speaker)}</strong>` : ""}${escapeHtml(line.text)}</div></div>`).join("") : `<div class="markdown">${escapeHtml(m.transcript_text)}</div>`) : `<div class="empty"><strong>${t("noTranscript")}</strong><p>${t("noTranscriptSub")}</p></div>`}`;
  bindRetranscribe(m);
}

function bindRetranscribe(m) {
  const btn = document.getElementById("retranscribeBtn");
  const mount = document.getElementById("retranscribeJob");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    await runJob("transcribe", { meeting: m.path, force: true }, mount, {
      onDone: async () => {
        await refreshMeeting(m.path);
      },
    });
    btn.disabled = false;
  });
}

function renderReport(body, m) {
  const reportSections = renderMarkdownSections(m.report_text);
  body.innerHTML = `
    ${m.report_stale ? `<div class="panel warn">${t("reportStale")}</div>` : ""}
    <div class="panel report-context">
      <div>
        <strong>report.md</strong>
        <div class="meeting-meta">
          <span class="badge type">${escapeHtml(m.meeting_type || "general")}</span>
          <span class="badge">${escapeHtml(m.llm_profile || "LLM profile unknown")}</span>
          <span class="badge">${escapeHtml(m.llm_model || m.report_model || "model unknown")}</span>
          <span>${escapeHtml(m.language || "auto")}</span>
        </div>
      </div>
      <div class="action-with-status">
        <button class="secondary-button" id="regenerateBtn" type="button">${t("regenerateReport")}</button>
        <span class="job-mount" id="regenerateJob"></span>
      </div>
    </div>
    ${m.report_text ? `<div class="report-sections">${reportSections}</div>` : `<div class="empty"><strong>${t("noReport")}</strong><p>${t("noReportSub")}</p></div>`}`;
  wireJobButton(
    document.getElementById("regenerateBtn"),
    document.getElementById("regenerateJob"),
    "summarize",
    { meeting: m.path, force: true },
    { needsConfirm: true, onDone: async () => { await refreshMeeting(m.path); } },
  );
}

function renderAudio(body, m) {
  body.innerHTML = `
    ${m.health.normalized_mismatch ? `<div class="panel warn"><strong>${escapeHtml(m.health.label)}</strong><p>${escapeHtml(m.health.detail)}</p>${gapButton("repairBackend")}</div>` : ""}
    <div class="grid-2">
      ${metric("Original", `${m.audio.original?.duration_label || "?"} · ${m.audio.original?.name || ""}`)}
      ${metric("Normalized", `${m.audio.normalized?.duration_label || "?"} · ${m.audio.normalized?.name || ""}`)}
    </div>
    <div class="panel"><h2>Files</h2><div class="mono muted">${escapeHtml(m.path)}</div></div>`;
}

function renderAudioTab(body, m) {
  const missingWarnings = [
    !m.audio.original ? t("sourceAudio") : null,
    !m.audio.normalized ? t("normalizedAudio") : null,
  ].filter(Boolean);
  body.innerHTML = `
    ${m.health.normalized_mismatch ? `<div class="panel warn"><strong>${escapeHtml(m.health.label)}</strong><p>${escapeHtml(m.health.detail)}</p></div>` : ""}
    ${missingWarnings.length ? `<div class="panel warn"><strong>${t("missingAudio")}</strong><p>${escapeHtml(missingWarnings.join(", "))}</p></div>` : ""}
    <div class="panel report-context">
      <div>
        <strong>Audio artifacts</strong>
        <div class="meeting-meta">
          <span class="badge ${m.health.level === "ok" ? "good" : "warn"}">${escapeHtml(m.health.label)}</span>
          <span>${escapeHtml(m.duration_label || "duration unknown")}</span>
        </div>
      </div>
      <div class="action-with-status">
        <button class="secondary-button" id="repairBtn" type="button">${t("repairAudio")}</button>
        <span class="job-mount" id="repairJob"></span>
      </div>
    </div>
    <div class="grid-2 audio-grid">
      ${audioArtifact(t("sourceAudio"), m.audio.original)}
      ${audioArtifact(t("normalizedAudio"), m.audio.normalized)}
    </div>
    <div class="panel"><h2>Files</h2><div class="mono muted">${escapeHtml(m.path)}</div></div>`;
  wireJobButton(
    document.getElementById("repairBtn"),
    document.getElementById("repairJob"),
    "repair",
    { meeting: m.path },
    { onDone: async () => { await refreshMeeting(m.path); } },
  );
}

function renderMetadata(body, m) {
  const coreRows = [
    ["Title", m.title],
    ["Date", formatDate(m.created_at)],
    ["Type", m.meeting_type],
    ["Project", m.project],
    ["Attendees", (m.attendees || []).join(", ")],
    ["Language", m.language],
    ["Share policy", m.share_policy],
  ];
  const modelRows = [
    ["Transcription backend", m.transcription_backend],
    ["Whisper model", m.transcription_model],
    ["Whisper device", m.transcription_device],
    ["Whisper compute", m.transcription_compute_type],
    ["LLM profile", m.llm_profile],
    ["Meeting ID", m.id],
    ["Path", m.path],
  ];
  body.innerHTML = `
    <div class="panel report-context">
      <div>
        <strong>${t("enrichMetadata")}</strong>
        <p class="muted">${t("metadataReadonly")}</p>
      </div>
      <div class="action-with-status">
        <button class="secondary-button" id="enrichBtn" type="button">${t("enrichMetadata")}</button>
        <span class="job-mount" id="enrichJob"></span>
      </div>
    </div>
    <div class="grid-2">
      ${metadataPanel("Core metadata", coreRows)}
      ${metadataPanel("Model and files", modelRows)}
    </div>
    ${metadataSuggestions(m.metadata_suggestions)}`;
  wireJobButton(
    document.getElementById("enrichBtn"),
    document.getElementById("enrichJob"),
    "enrich",
    { meeting: m.path, force: true },
    { needsConfirm: true, onDone: async () => { await refreshMeeting(m.path); } },
  );
  bindMetadataApply(m);
}

// Apply a confirmed suggestion to metadata.json via the safe-write endpoint.
// The meeting path can change (a title apply renames the folder), so we adopt
// the returned record and re-point the selection before re-rendering.
async function applySuggestion(m, updates, mount) {
  try {
    const updated = await apiPost("/api/meeting/apply", { meeting: m.path, updates });
    const idx = (state.data?.meetings || []).findIndex((x) => x.path === m.path);
    if (idx >= 0) state.data.meetings[idx] = updated;
    state.selectedPath = updated.path;
    render();
  } catch (err) {
    flashStatus(mount, false, `${t("saveFailed")}: ${err.message}`);
  }
}

function bindMetadataApply(m) {
  const s = m.metadata_suggestions;
  if (!s || s.error) return;
  const mount = document.getElementById("applyStatus");
  const wire = (id, buildUpdates, { confirmMessage } = {}) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.addEventListener("click", async () => {
      if (confirmMessage && !window.confirm(confirmMessage)) return;
      btn.disabled = true;
      await applySuggestion(m, buildUpdates(), mount);
    });
  };
  if (s.suggested_title) wire("applyTitle", () => ({ title: s.suggested_title }), { confirmMessage: `${t("apply")}: "${s.suggested_title}"? (folder rename)` });
  if (s.suggested_meeting_type) wire("applyType", () => ({ meeting_type: s.suggested_meeting_type }));
  if (s.suggested_project) wire("applyProject", () => ({ project: s.suggested_project }));
  if (s.suggested_attendees && s.suggested_attendees.length) wire("applyAttendees", () => ({ attendees: s.suggested_attendees }));
}

function renderSettings() {
  const main = document.getElementById("main");
  main.innerHTML = "";
  main.appendChild(cloneTemplate("settingsTemplate"));
  applyPrefs();
  document.getElementById("appLanguage").value = state.lang;
  document.getElementById("appLanguage").addEventListener("change", (ev) => {
    state.lang = ev.target.value;
    localStorage.setItem("manola.appLanguage", state.lang);
    renderSettings();
  });
  document.getElementById("highlightColor").value = state.highlight;
  document.getElementById("highlightColor").addEventListener("input", (ev) => {
    state.highlight = ev.target.value;
    localStorage.setItem("manola.highlightColor", state.highlight);
    applyPrefs();
  });
  document.getElementById("resetHighlight").addEventListener("click", () => {
    state.highlight = "#3a6ae0";
    localStorage.setItem("manola.highlightColor", state.highlight);
    renderSettings();
  });

  const config = state.data.config;
  const profiles = Object.keys(config.llm_profiles || {});
  // Editable rows write to ~/.manola/config.toml via POST /api/config.
  const editable = [
    [t("archive"), [
      ["workspace_dir", t("workspaceDir"), "text", config.workspace_dir],
    ]],
    [t("transcription"), [
      ["default_language", t("transcriptLanguage"), "text", config.default_language],
      ["default_transcription_backend", "Backend", "select", config.default_transcription_backend, ["local", "remote"]],
      ["local_whisper_model", t("model"), "text", config.local_whisper_model],
      ["local_whisper_device", t("device"), "select", config.local_whisper_device, ["cpu", "cuda"]],
      ["local_whisper_compute_type", t("computeType"), "text", config.local_whisper_compute_type],
    ]],
    [t("reports"), [
      ["default_llm_profile", t("defaultLlmProfile"), "select", config.default_llm_profile, profiles],
      ["default_generate_llm_report", t("generateReports"), "bool", config.default_generate_llm_report],
    ]],
    [t("sharing"), [
      ["shared_dir", t("sharedDir"), "text", config.shared_dir || ""],
    ]],
  ];
  const readonly = [
    [t("advanced"), [
      ["Models directory", config.models_dir],
      ["Prompts directory", config.prompts_dir],
      ["Profiles", profiles.join(", ") || "none"],
      ["Config", config.config_path],
      ["Secrets", config.secrets_path],
    ]],
  ];
  const holder = document.getElementById("settingsSections");
  holder.innerHTML =
    editable.map(([title, rows]) => `
      <div class="settings-section">
        <h2>${escapeHtml(title)}</h2>
        ${rows.map((row) => settingControl(...row)).join("")}
      </div>`).join("") +
    `<div class="settings-section readonly-config"><h2>${t("backendConfig")}</h2><p class="muted">${t("backendConfigSub")}</p></div>` +
    readonly.map(([title, rows]) => `
      <div class="settings-section">
        <h2>${escapeHtml(title)}</h2>
        ${rows.map(([k, v]) => `<div class="setting-row"><div><div class="setting-title">${escapeHtml(k)}</div><div class="setting-sub">Read-only Manola config</div></div><div class="control mono readonly-value" aria-readonly="true">${escapeHtml(String(v))}</div></div>`).join("")}
      </div>`).join("");
  editable.forEach(([, rows]) => rows.forEach((row) => bindSettingControl(row[0], row[2])));
}

function settingControl(field, label, kind, value, options) {
  let control;
  if (kind === "select") {
    control = `<select id="cfg_${field}" class="control sort-select">${(options || []).map((o) => `<option value="${escapeHtml(o)}" ${String(o) === String(value) ? "selected" : ""}>${escapeHtml(o)}</option>`).join("")}</select>`;
  } else if (kind === "bool") {
    control = `<select id="cfg_${field}" class="control sort-select"><option value="true" ${value ? "selected" : ""}>true</option><option value="false" ${value ? "" : "selected"}>false</option></select>`;
  } else {
    control = `<input id="cfg_${field}" class="control" type="text" value="${escapeHtml(value ?? "")}" />`;
  }
  return `<div class="setting-row">
    <div><div class="setting-title">${escapeHtml(label)}</div><div class="setting-sub mono">${escapeHtml(field)}</div></div>
    <div class="control-group">${control}<span class="job-mount" id="st_${field}"></span></div>
  </div>`;
}

function bindSettingControl(field, kind) {
  const input = document.getElementById(`cfg_${field}`);
  if (!input) return;
  const event = kind === "text" ? "change" : "change";
  input.addEventListener(event, () => saveConfig(field, input.value, document.getElementById(`st_${field}`)));
}

async function saveConfig(field, value, mount) {
  try {
    const updated = await apiPost("/api/config", { [field]: value });
    state.data.config = updated;
    flashStatus(mount, true);
  } catch (err) {
    flashStatus(mount, false, `${t("saveFailed")}: ${err.message}`);
  }
}

function renderDevices() {
  const report = state.data.devices;
  const config = state.data.config;
  renderSimple(t("devices"), t("devicesSub"), () => {
    if (report.error) return `<div class="panel warn">${escapeHtml(report.error)}</div>`;
    const micOptions = deviceSelect("cfg_default_mic_index", report.microphones, config.default_mic_index);
    const spkOptions = deviceSelect("cfg_default_speaker_index", report.speakers, config.default_speaker_index);
    return `
      <div class="panel report-context">
        <div>
          <strong>Capture readiness</strong>
          <div class="meeting-meta">
            <span class="badge ${report.microphones?.length ? "good" : "warn"}">${report.microphones?.length || 0} microphones</span>
            <span class="badge ${report.speakers?.length ? "good" : "warn"}">${report.speakers?.length || 0} speakers</span>
            <span class="badge ${report.loopbacks?.length ? "good" : "warn"}">${report.loopbacks?.length || 0} loopbacks</span>
          </div>
        </div>
      </div>
      <div class="panel">
        <h2>Default capture devices</h2>
        <div class="setting-row"><div><div class="setting-title">${t("microphone")}</div><div class="setting-sub mono">default_mic_index</div></div><div class="control-group">${micOptions}</div></div>
        <div class="setting-row"><div><div class="setting-title">${t("speakerLoopback")}</div><div class="setting-sub mono">default_speaker_index</div></div><div class="control-group">${spkOptions}</div></div>
        <div class="metadata-actions">
          <button class="secondary-button" id="saveDevicesBtn" type="button">${t("saveDevices")}</button>
          <span class="job-mount" id="saveDevicesStatus"></span>
        </div>
      </div>
      <div class="grid-2">
        ${deviceList("Microphones", report.microphones, report.default_microphone)}
        ${deviceList("Speakers", report.speakers, report.default_speaker)}
      </div>
      <div class="panel"><h2>Loopbacks</h2>${(report.loopbacks || []).map((d) => `<div class="setting-row"><span class="status-dot ok"></span><div>${escapeHtml(d)}</div></div>`).join("") || "<p class='muted'>None detected.</p>"}</div>`;
  });
  bindDeviceSave();
}

// Build a device picker. Value is the 1-based index used by `manola audio setup`,
// or empty for the system default.
function deviceSelect(id, devices, selectedIndex) {
  const opts = [`<option value="" ${selectedIndex === null || selectedIndex === undefined ? "selected" : ""}>${t("systemDefault")}</option>`]
    .concat((devices || []).map((d, i) => {
      const idx = i + 1;
      return `<option value="${idx}" ${String(idx) === String(selectedIndex) ? "selected" : ""}>${idx} — ${escapeHtml(d)}</option>`;
    }));
  return `<select id="${id}" class="control sort-select">${opts.join("")}</select>`;
}

function bindDeviceSave() {
  const btn = document.getElementById("saveDevicesBtn");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const mic = document.getElementById("cfg_default_mic_index").value;
    const spk = document.getElementById("cfg_default_speaker_index").value;
    const mount = document.getElementById("saveDevicesStatus");
    btn.disabled = true;
    try {
      const updated = await apiPost("/api/config", { default_mic_index: mic, default_speaker_index: spk });
      state.data.config = updated;
      flashStatus(mount, true);
    } catch (err) {
      flashStatus(mount, false, `${t("saveFailed")}: ${err.message}`);
    }
    btn.disabled = false;
  });
}

function renderDoctor() {
  renderSimple(t("doctor"), t("doctorSub"), () => `
    <div class="panel report-context">
      <div>
        <strong>Diagnostics</strong>
        <div class="meeting-meta">
          <span class="badge good">${state.data.doctor.filter((c) => c.status === "ok").length} ok</span>
          <span class="badge warn">${state.data.doctor.filter((c) => c.status === "warn").length} warn</span>
          <span class="badge bad">${state.data.doctor.filter((c) => c.status === "error").length} error</span>
        </div>
      </div>
      <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("rerunDoctor")}</button>
    </div>
    ${state.data.doctor.map((c) => `<div class="panel"><span class="badge ${c.status === "ok" ? "good" : c.status === "warn" ? "warn" : "bad"}">${escapeHtml(c.status)}</span> <strong>${escapeHtml(c.name)}</strong><div class="mono muted">${escapeHtml(c.detail)}</div></div>`).join("")}
    ${commandPanel("Doctor CLI checks", ["uv run manola doctor", "uv run manola audio doctor"])}`);
}

function renderImport() {
  const config = state.data.config;
  renderSimple(t("importAudio"), t("importSub"), () => `
    <div class="panel warn report-context">
      <div>
        <strong>${t("backendGap")}</strong>
        <p class="muted">Browser import needs a file upload endpoint or desktop file-picker handoff before choose/process can run.</p>
      </div>
      <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("chooseAudio")}</button>
    </div>
    <div class="grid-2">
      <div class="panel">
        <h2>Source</h2>
        <div class="setting-row"><span>Audio file</span><div class="control readonly-value" aria-readonly="true">No file selected</div></div>
        <div class="setting-row"><span>Transcript source</span><div class="control readonly-value" aria-readonly="true">Audio transcription</div></div>
        <div class="setting-row"><span>Google Recorder</span><div class="control readonly-value" aria-readonly="true">Not connected</div></div>
      </div>
      <div class="panel">
        <h2>Meeting metadata</h2>
        <div class="setting-row"><span>Title</span><div class="control readonly-value" aria-readonly="true">Imported audio</div></div>
        <div class="setting-row"><span>Language</span><div class="control readonly-value" aria-readonly="true">${escapeHtml(config.default_language || "auto")}</div></div>
        <div class="setting-row"><span>Project</span><div class="control readonly-value" aria-readonly="true">none</div></div>
        <div class="setting-row"><span>Share policy</span><div class="control readonly-value" aria-readonly="true">private</div></div>
      </div>
    </div>
    <div class="panel">
      <h2>Proposed folder</h2>
      <div class="mono">Meetings/YYYY-MM-DD__general__imported-audio</div>
    </div>
    <div class="panel">
      <h2>Pipeline</h2>
      ${importPipelineRows()}
      <div class="metadata-actions">
        <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("chooseAudio")}</button>
        <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("processImport")}</button>
      </div>
    </div>
    ${commandPanel("Import with CLI", ["uv run manola import <audio-path> --language en", "uv run manola process <audio-path> --language es --share all"])}`);
}

function renderRecord() {
  const config = state.data.config;
  const recording = !!state.recordingJobId;
  const micLabel = config.default_mic_index ?? t("systemDefault");
  const spkLabel = config.default_speaker_index ?? t("systemDefault");
  renderSimple(t("recordMeeting"), t("recordSub"), () => `
    <div class="grid-2">
      <div class="panel">
        <h2>Meeting</h2>
        <div class="setting-row"><span>Title</span><input id="recTitle" class="control" type="text" placeholder="New meeting" ${recording ? "disabled" : ""} /></div>
        <div class="setting-row"><span>${t("transcriptLanguage")}</span><input id="recLanguage" class="control" type="text" value="${escapeHtml(config.default_language || "auto")}" ${recording ? "disabled" : ""} /></div>
        <div class="setting-row"><span>Type</span><select id="recType" class="control sort-select" ${recording ? "disabled" : ""}>${MEETING_TYPES.map((tp) => `<option value="${tp}">${escapeHtml(tp)}</option>`).join("")}</select></div>
        <div class="setting-row"><span>${t("sharePolicy")}</span><select id="recShare" class="control sort-select" ${recording ? "disabled" : ""}>${SHARE_POLICIES.map((p) => `<option value="${p}">${escapeHtml(p)}</option>`).join("")}</select></div>
      </div>
      <div class="panel">
        <h2>Capture</h2>
        <div class="setting-row"><span>${t("microphone")}</span><strong>${escapeHtml(String(micLabel))}</strong></div>
        <div class="setting-row"><span>${t("speakerLoopback")}</span><strong>${escapeHtml(String(spkLabel))}</strong></div>
        <div class="setting-row"><label for="recAllowPartial">${t("allowPartial")}</label><input id="recAllowPartial" type="checkbox" checked ${recording ? "disabled" : ""} /></div>
        <p class="setting-sub">${t("allowPartialSub")}</p>
        <p class="setting-sub">${t("recordLiveLater")}</p>
      </div>
    </div>
    <div class="panel">
      <h2>${t("recordMeeting")}</h2>
      <p class="setting-sub">${t("recordReportNote")}</p>
      <div class="action-with-status">
        <button class="secondary-button" id="recStartBtn" type="button" ${recording ? "disabled" : ""}>${t("startRecording")}</button>
        <button class="secondary-button" id="recStopBtn" type="button" ${recording ? "" : "disabled"}>${t("stopRecording")}</button>
        <span class="job-mount" id="recStatus"></span>
      </div>
      <div class="meter-row"><span>MIC</span><div class="static-meter"><span id="recMeterMic" style="width:0%"></span></div></div>
      <div class="meter-row"><span>SYS</span><div class="static-meter"><span id="recMeterSys" style="width:0%"></span></div></div>
    </div>
    <div class="panel">
      <h2>${t("liveTranscript")}</h2>
      <div id="recPreview" class="live-preview"><p class="muted">${t("recordPreviewEmpty")}</p></div>
    </div>`);
  bindRecord();
}

// Poll the lightweight recording-live endpoint (~400ms) for meters + preview.
// This is the ADR-0003 streaming seam, scoped to recording, done as chunked
// polling rather than SSE to keep the stdlib server and no build system.
function startLivePolling(jobId) {
  let since = 0;
  const preview = document.getElementById("recPreview");
  let cleared = false;
  const setMeter = (id, rms) => {
    const el = document.getElementById(id);
    if (!el) return;
    // RMS is roughly 0..0.3 for speech; scale to a readable bar.
    const pct = Math.max(0, Math.min(100, Math.round((rms || 0) * 400)));
    el.style.width = `${pct}%`;
  };
  const tick = async () => {
    if (state.recordingJobId !== jobId) return;
    let snap;
    try {
      snap = await api(`/api/recording/live?job_id=${jobId}&since=${since}`);
    } catch {
      return; // job may have ended; pollJob handles terminal state
    }
    if (snap.levels) {
      setMeter("recMeterMic", snap.levels.mic);
      setMeter("recMeterSys", snap.levels.system);
    }
    if (snap.preview && snap.preview.length && preview) {
      if (!cleared) { preview.innerHTML = ""; cleared = true; }
      snap.preview.forEach((line) => {
        const div = document.createElement("div");
        div.className = "transcript-line";
        div.innerHTML = `<div>${escapeHtml(line)}</div>`;
        preview.appendChild(div);
      });
      preview.scrollTop = preview.scrollHeight;
    }
    since = snap.preview_total ?? since;
    if (state.recordingJobId === jobId && snap.status === "running") {
      setTimeout(tick, 400);
    }
  };
  tick();
}

function bindRecord() {
  const startBtn = document.getElementById("recStartBtn");
  const stopBtn = document.getElementById("recStopBtn");
  const mount = document.getElementById("recStatus");
  if (startBtn) {
    startBtn.addEventListener("click", async () => {
      const params = {
        title: document.getElementById("recTitle").value || undefined,
        language: document.getElementById("recLanguage").value || undefined,
        meeting_type: document.getElementById("recType").value,
        share_policy: document.getElementById("recShare").value,
        allow_partial: document.getElementById("recAllowPartial").checked,
      };
      let job;
      try {
        job = await apiPost("/api/jobs/record", params);
      } catch (err) {
        flashStatus(mount, false, `${t("jobFailed")}: ${err.message}`);
        return;
      }
      state.recordingJobId = job.id;
      startBtn.disabled = true;
      stopBtn.disabled = false;
      startLivePolling(job.id);
      pollJob(job.id, mount, async (result) => {
        state.recordingJobId = null;
        state.data = await api("/api/state");
        if (result && result.meeting) {
          state.selectedPath = result.meeting;
          state.view = "archive";
        }
        render();
      });
    });
  }
  if (stopBtn) {
    stopBtn.addEventListener("click", async () => {
      if (!state.recordingJobId) return;
      stopBtn.disabled = true;
      try {
        await apiPost("/api/recording/stop", { job_id: state.recordingJobId });
      } catch (err) {
        flashStatus(mount, false, `${t("saveFailed")}: ${err.message}`);
      }
    });
  }
}

function renderSimple(title, sub, content) {
  const main = document.getElementById("main");
  main.innerHTML = "";
  main.appendChild(cloneTemplate("simplePageTemplate"));
  document.getElementById("simpleTitle").textContent = title;
  document.getElementById("simpleSub").textContent = sub;
  document.getElementById("simpleContent").innerHTML = typeof content === "function" ? content() : content;
}

function metric(label, value) {
  return `<div class="panel"><div class="muted">${escapeHtml(label)}</div><div style="font-size:18px;font-weight:650">${escapeHtml(String(value))}</div></div>`;
}

function audioArtifact(label, artifact) {
  if (!artifact) {
    return `<div class="panel audio-artifact missing"><h2>${escapeHtml(label)}</h2><p class="muted">${t("missingAudio")}</p></div>`;
  }
  const rows = [
    ["File", artifact.name],
    ["Duration", artifact.duration_label || "unknown"],
    ["Sample rate", artifact.sample_rate ? `${artifact.sample_rate} Hz` : "unknown"],
    ["Channels", artifact.channels || "unknown"],
    ["Size", artifact.size_bytes ? formatBytes(artifact.size_bytes) : "unknown"],
  ];
  return `<div class="panel audio-artifact">
    <h2>${escapeHtml(label)}</h2>
    ${rows.map(([key, value]) => `<div class="setting-row"><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}
    <div class="mono muted audio-path">${escapeHtml(artifact.path || "")}</div>
  </div>`;
}

function metadataPanel(title, rows) {
  return `<div class="panel metadata-panel">
    <h2>${escapeHtml(title)}</h2>
    ${rows.map(([key, value]) => `<div class="setting-row"><span>${escapeHtml(key)}</span><strong>${metadataValue(value)}</strong></div>`).join("")}
  </div>`;
}

function metadataValue(value) {
  if (Array.isArray(value)) return escapeHtml(value.length ? value.join(", ") : "none");
  if (value === null || value === undefined || value === "") return `<span class="muted">none</span>`;
  return escapeHtml(String(value));
}

function metadataSuggestions(suggestions) {
  if (!suggestions) {
    return `<div class="panel metadata-suggestions"><h2>Metadata suggestions</h2><p class="muted">${t("noSuggestions")}</p></div>`;
  }
  if (suggestions.error) {
    return `<div class="panel warn"><strong>Metadata suggestions</strong><p>${escapeHtml(suggestions.error)}</p></div>`;
  }
  // Applyable fields get an Apply button; the rest are informational.
  const applyable = [
    ["Suggested title", suggestions.suggested_title, "applyTitle"],
    ["Suggested type", suggestions.suggested_meeting_type, "applyType"],
    ["Suggested project", suggestions.suggested_project, "applyProject"],
    ["Suggested attendees", suggestions.suggested_attendees || [], "applyAttendees"],
  ];
  const info = [
    ["Notable terms", suggestions.notable_terms || []],
    ["Summary", suggestions.summary],
    ["Confidence notes", suggestions.confidence_notes || []],
  ];
  const corrections = suggestions.possible_name_corrections || [];
  const hasValue = (v) => Array.isArray(v) ? v.length > 0 : v !== null && v !== undefined && v !== "";
  return `<div class="panel metadata-suggestions">
    <div class="report-context">
      <h2>Metadata suggestions</h2>
      <span class="job-mount" id="applyStatus"></span>
    </div>
    ${applyable.map(([key, value, id]) => `<div class="setting-row"><span>${escapeHtml(key)}</span><strong>${metadataValue(value)}</strong>${hasValue(value) ? `<button class="secondary-button small" id="${id}" type="button">${t("apply")}</button>` : ""}</div>`).join("")}
    ${info.map(([key, value]) => `<div class="setting-row"><span>${escapeHtml(key)}</span><strong>${metadataValue(value)}</strong></div>`).join("")}
    ${corrections.length ? `<h3>Name corrections</h3>${corrections.map((item) => `<div class="setting-row"><span>${escapeHtml(item.heard_as || "unknown")}</span><strong>${escapeHtml(item.suggested || "unknown")}</strong></div><div class="setting-sub">${escapeHtml([item.confidence ? `confidence: ${item.confidence}` : "", item.evidence ? `evidence: ${item.evidence}` : ""].filter(Boolean).join(" · ") || "no confidence detail")}</div>`).join("")}` : ""}
  </div>`;
}

function pipelineRows(m) {
  const rows = [
    ["Audio recorded", !!m.audio.original],
    ["Normalized", !!m.audio.normalized],
    ["Transcribed", !!m.transcript_text],
    ["Report generated", !!m.report_text],
  ];
  return rows.map(([label, ok]) => `<div class="setting-row"><span class="status-dot ${ok ? "ok" : "warn"}"></span><span>${escapeHtml(label)}</span></div>`).join("");
}

function importPipelineRows() {
  return ["Copy original", "Normalize", "Transcribe", "Summarize", "Export"].map((label) => `<div class="setting-row"><span class="status-dot warn"></span><span>${escapeHtml(label)}</span><span class="badge">pending</span></div>`).join("");
}

function deviceList(title, devices, defaultName) {
  return `<div class="panel"><h2>${escapeHtml(title)}</h2>${(devices || []).map((d, i) => `<div class="setting-row"><span class="status-dot ok"></span><span class="mono muted">${i + 1}</span><span>${escapeHtml(d)}</span>${d === defaultName ? `<span class="badge good">default</span>` : `<span class="badge">detected</span>`}</div>`).join("") || "<p class='muted'>None detected.</p>"}</div>`;
}

function commandPanel(title, commands) {
  return `<div class="panel command-panel">
    <div class="report-context">
      <h2>${escapeHtml(title)}</h2>
      ${disabledAction(t("runCli"), "jobBackend")}
    </div>
    ${commands.map((command) => `<div class="setting-row"><span class="mono">${escapeHtml(command)}</span></div>`).join("")}
  </div>`;
}

function disabledAction(label, area) {
  return `<button class="secondary-button disabled-action" type="button" title="${escapeHtml(backendGapDetail(area))}">${escapeHtml(label)}</button>`;
}

function gapBlock(text) {
  return `<div class="panel warn"><strong>${t("backendGap")}</strong><p>${escapeHtml(text)}</p></div>`;
}

function gapButton(area) {
  return disabledAction(t("unavailable"), area);
}

function backendGapDetail(area) {
  const gaps = {
    exportBackend: "Export needs an async backend job endpoint before the UI can run it.",
    jobBackend: "This UI action needs a backend job endpoint before it can run.",
    metadataBackend: "Metadata enrichment and apply/save need write endpoints before the UI can run them.",
    repairBackend: "Audio repair needs a tracked backend repair job before the UI can run it.",
    reportBackend: "Report regeneration needs an async summarize job before the UI can run it.",
    transcribeBackend: "Retranscription needs an async transcription job before the UI can run it.",
  };
  return gaps[area] || "This action is unavailable until the backend API exists.";
}

function renderMarkdownSections(text) {
  const sections = markdownSections(text);
  return sections.map((section) => `
    <section class="report-section">
      ${section.title ? `<h2>${escapeHtml(section.title)}</h2>` : ""}
      ${section.lines.length ? markdownLines(section.lines) : ""}
    </section>`).join("");
}

function markdownSections(text) {
  const sections = [];
  let current = { title: "", lines: [] };
  (text || "").split(/\r?\n/).forEach((line) => {
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      if (current.title || current.lines.length) sections.push(current);
      current = { title: heading[2], lines: [] };
    } else {
      current.lines.push(line);
    }
  });
  if (current.title || current.lines.some((line) => line.trim())) sections.push(current);
  return sections.length ? sections : [{ title: "", lines: text ? [text] : [] }];
}

function markdownLines(lines) {
  const blocks = [];
  let bullets = [];
  let paragraph = [];
  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(`<p>${escapeHtml(paragraph.join(" "))}</p>`);
    paragraph = [];
  };
  const flushBullets = () => {
    if (!bullets.length) return;
    blocks.push(`<ul>${bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`);
    bullets = [];
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      flushBullets();
      return;
    }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      bullets.push(bullet[1]);
      return;
    }
    flushBullets();
    paragraph.push(trimmed);
  });
  flushParagraph();
  flushBullets();
  return blocks.join("");
}

function parseTranscript(text) {
  if (!text) return [];
  return text.split(/\r?\n/).map((line) => {
    const timestamped = line.match(/^\[([^\]]+)\]\s*(.*)$/);
    const body = timestamped ? timestamped[2] : line.trim();
    const speaker = body.match(/^([^:]{1,48}):\s+(.+)$/);
    if (timestamped || speaker) {
      return {
        time: timestamped?.[1] || "",
        speaker: speaker?.[1] || "",
        text: speaker?.[2] || body,
      };
    }
    return null;
  }).filter(Boolean);
}

function formatDate(value) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat(state.lang === "es" ? "es-ES" : "en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
  } catch {
    return value;
  }
}

function formatDay(value) {
  if (!value) return "Unknown date";
  try {
    return new Intl.DateTimeFormat(state.lang === "es" ? "es-ES" : "en-US", { weekday: "short", month: "short", day: "numeric" }).format(new Date(value));
  } catch {
    return value;
  }
}

function formatTime(value) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat(state.lang === "es" ? "es-ES" : "en-US", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
  } catch {
    return value;
  }
}

function dayKey(value) {
  if (!value) return "unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().slice(0, 10);
}

function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes)) return "unknown";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let size = bytes / 1024;
  let unit = units.shift();
  while (size >= 1024 && units.length) {
    size /= 1024;
    unit = units.shift();
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${unit}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" })[c]);
}

boot().catch((err) => {
  document.getElementById("main").innerHTML = `<section class="page"><div class="panel warn"><strong>Failed to load UI</strong><pre>${escapeHtml(err.stack || err.message || err)}</pre></div></section>`;
});
