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
};

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
  drawMeetingList();
  renderDetail();
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
  const meetings = filteredMeetings();
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
    ${disabledWorkflowPanel(m)}`;
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
      <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("retranscribe")}</button>
    </div>
    ${m.transcript_text ? (lines.length ? lines.map((line) => `<div class="transcript-line"><div class="timestamp">${escapeHtml(line.time || "")}</div><div>${line.speaker ? `<strong class="speaker">${escapeHtml(line.speaker)}</strong>` : ""}${escapeHtml(line.text)}</div></div>`).join("") : `<div class="markdown">${escapeHtml(m.transcript_text)}</div>`) : `<div class="empty"><strong>${t("noTranscript")}</strong><p>${t("noTranscriptSub")}</p>${gapButton("transcribeBackend")}</div>`}`;
}

function renderReport(body, m) {
  const reportSections = renderMarkdownSections(m.report_text);
  body.innerHTML = `
    ${m.report_stale ? `<div class="panel warn">${t("reportStale")} ${gapButton("reportBackend")}</div>` : ""}
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
      <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("regenerateReport")}</button>
    </div>
    ${m.report_text ? `<div class="report-sections">${reportSections}</div>` : `<div class="empty"><strong>${t("noReport")}</strong><p>${t("noReportSub")}</p>${gapButton("reportBackend")}</div>`}`;
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
    ${m.health.normalized_mismatch ? `<div class="panel warn"><strong>${escapeHtml(m.health.label)}</strong><p>${escapeHtml(m.health.detail)}</p>${gapButton("repairBackend")}</div>` : ""}
    ${missingWarnings.length ? `<div class="panel warn"><strong>${t("missingAudio")}</strong><p>${escapeHtml(missingWarnings.join(", "))}</p>${gapButton("repairBackend")}</div>` : ""}
    <div class="panel report-context">
      <div>
        <strong>Audio artifacts</strong>
        <div class="meeting-meta">
          <span class="badge ${m.health.level === "ok" ? "good" : "warn"}">${escapeHtml(m.health.label)}</span>
          <span>${escapeHtml(m.duration_label || "duration unknown")}</span>
        </div>
      </div>
      <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("repairAudio")}</button>
    </div>
    <div class="grid-2 audio-grid">
      ${audioArtifact(t("sourceAudio"), m.audio.original)}
      ${audioArtifact(t("normalizedAudio"), m.audio.normalized)}
    </div>
    <div class="panel"><h2>Files</h2><div class="mono muted">${escapeHtml(m.path)}</div></div>`;
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
    <div class="panel warn report-context">
      <div>
        <strong>${t("metadataReadonly")}</strong>
        <p class="muted">Edit, save, accept, reject, and apply controls are intentionally disabled because metadata write endpoints do not exist yet.</p>
      </div>
      <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("saveMetadata")}</button>
    </div>
    <div class="grid-2">
      ${metadataPanel("Core metadata", coreRows)}
      ${metadataPanel("Model and files", modelRows)}
    </div>
    ${metadataSuggestions(m.metadata_suggestions)}`;
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
  const sections = [
    [t("archive"), [[t("workspaceDir"), config.workspace_dir], ["Models directory", config.models_dir]]],
    [t("transcription"), [[t("transcriptLanguage"), config.default_language], ["Backend", config.default_transcription_backend], [t("model"), config.local_whisper_model], [t("device"), config.local_whisper_device], [t("computeType"), config.local_whisper_compute_type], ["Chunk seconds", config.local_whisper_chunk_seconds], ["Live model", config.live_transcript_model], ["Live device", config.live_transcript_device], ["Live compute", config.live_transcript_compute_type]]],
    [t("reports"), [[t("defaultLlmProfile"), config.default_llm_profile], [t("generateReports"), String(config.default_generate_llm_report)], ["Profiles", Object.keys(config.llm_profiles || {}).join(", ") || "none"]]],
    [t("sharing"), [[t("sharedDir"), config.shared_dir || "not configured"]]],
    [t("prompts"), [["Prompts directory", config.prompts_dir]]],
    [t("advanced"), [["Config", config.config_path], ["Secrets", config.secrets_path], ["Default mic index", config.default_mic_index ?? "not configured"], ["Default speaker index", config.default_speaker_index ?? "not configured"]]],
  ];
  const holder = document.getElementById("settingsSections");
  holder.innerHTML = `<div class="settings-section readonly-config"><h2>${t("backendConfig")}</h2><p class="muted">${t("backendConfigSub")}</p></div>` + sections.map(([title, rows]) => `
    <div class="settings-section">
      <h2>${escapeHtml(title)}</h2>
      ${rows.map(([k, v]) => `<div class="setting-row"><div><div class="setting-title">${escapeHtml(k)}</div><div class="setting-sub">Read-only Manola config</div></div><div class="control mono readonly-value" aria-readonly="true">${escapeHtml(String(v))}</div></div>`).join("")}
    </div>`).join("");
}

function renderDevices() {
  renderSimple(t("devices"), t("devicesSub"), () => {
    const report = state.data.devices;
    if (report.error) return `<div class="panel warn">${escapeHtml(report.error)}</div>${commandPanel("Device CLI checks", ["uv run manola devices", "uv run manola audio doctor"])}`;
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
        <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("testDevices")}</button>
      </div>
      <div class="grid-2">
        ${deviceList("Microphones", report.microphones, report.default_microphone)}
        ${deviceList("Speakers", report.speakers, report.default_speaker)}
      </div>
      <div class="panel"><h2>Loopbacks</h2>${(report.loopbacks || []).map((d) => `<div class="setting-row"><span class="status-dot ok"></span><div>${escapeHtml(d)}</div></div>`).join("") || "<p class='muted'>None detected.</p>"}</div>
      ${commandPanel("Device CLI checks", ["uv run manola devices", "uv run manola audio setup", "uv run manola audio test --source meeting --duration 10"])}`;
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
  renderSimple(t("recordMeeting"), "Desktop-class recording flow is designed, but not wired in v1.", () => `
    <div class="panel warn report-context">
      <div>
        <strong>${t("backendGap")}</strong>
        <p class="muted">Recording from the browser needs a controllable recording job API plus live level/transcript events.</p>
      </div>
      <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("startRecording")}</button>
    </div>
    <div class="grid-2">
      <div class="panel">
        <h2>Meeting defaults</h2>
        <div class="setting-row"><span>Title</span><div class="control readonly-value" aria-readonly="true">New meeting</div></div>
        <div class="setting-row"><span>Language</span><div class="control readonly-value" aria-readonly="true">${escapeHtml(config.default_language || "auto")}</div></div>
        <div class="setting-row"><span>LLM profile</span><div class="control readonly-value" aria-readonly="true">${escapeHtml(config.default_llm_profile || "unknown")}</div></div>
        <div class="setting-row"><span>Share policy</span><div class="control readonly-value" aria-readonly="true">private</div></div>
      </div>
      <div class="panel">
        <h2>Capture defaults</h2>
        <div class="setting-row"><span>Microphone</span><strong>${escapeHtml(config.default_mic_index ?? "system default")}</strong></div>
        <div class="setting-row"><span>Speaker loopback</span><strong>${escapeHtml(config.default_speaker_index ?? "auto probe")}</strong></div>
        <div class="meter-row"><span>MIC</span><div class="static-meter"><span style="width:42%"></span></div></div>
        <div class="meter-row"><span>SYS</span><div class="static-meter"><span style="width:36%"></span></div></div>
      </div>
    </div>
    <div class="panel">
      <h2>${t("liveTranscript")}</h2>
      <div class="transcript-line placeholder"><div class="timestamp">00:00</div><div>Preview chunks will appear here after the UI has a live event stream.</div></div>
      <div class="metadata-actions">
        <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("startRecording")}</button>
        <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("stopRecording")}</button>
        <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("processRecording")}</button>
      </div>
    </div>
    ${commandPanel("Record with CLI", ["uv run manola meet --language en", "uv run manola meet --language es", "uv run manola record --source meeting --process --language en"])}`);
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
    <button class="secondary-button disabled-action" type="button" title="Backend gap">${t("saveMetadata")}</button>
  </div>`;
}

function metadataValue(value) {
  if (Array.isArray(value)) return escapeHtml(value.length ? value.join(", ") : "none");
  if (value === null || value === undefined || value === "") return `<span class="muted">none</span>`;
  return escapeHtml(String(value));
}

function metadataSuggestions(suggestions) {
  if (!suggestions) {
    return `<div class="panel metadata-suggestions"><h2>Metadata suggestions</h2><p class="muted">${t("noSuggestions")}</p>${disabledAction(t("applySuggestions"), "metadataBackend")}</div>`;
  }
  if (suggestions.error) {
    return `<div class="panel warn"><strong>Metadata suggestions</strong><p>${escapeHtml(suggestions.error)}</p>${gapButton("metadataBackend")}</div>`;
  }
  const rows = [
    ["Suggested title", suggestions.suggested_title],
    ["Suggested type", suggestions.suggested_meeting_type],
    ["Suggested project", suggestions.suggested_project],
    ["Suggested attendees", suggestions.suggested_attendees || []],
    ["Notable terms", suggestions.notable_terms || []],
    ["Summary", suggestions.summary],
    ["Confidence notes", suggestions.confidence_notes || []],
  ];
  const corrections = suggestions.possible_name_corrections || [];
  return `<div class="panel metadata-suggestions">
    <div class="report-context">
      <h2>Metadata suggestions</h2>
      ${disabledAction(t("applySuggestions"), "metadataBackend")}
    </div>
    ${rows.map(([key, value]) => `<div class="setting-row"><span>${escapeHtml(key)}</span><strong>${metadataValue(value)}</strong></div>`).join("")}
    ${corrections.length ? `<h3>Name corrections</h3>${corrections.map((item) => `<div class="setting-row"><span>${escapeHtml(item.heard_as || "unknown")}</span><strong>${escapeHtml(item.suggested || "unknown")}</strong></div><div class="setting-sub">${escapeHtml([item.confidence ? `confidence: ${item.confidence}` : "", item.evidence ? `evidence: ${item.evidence}` : ""].filter(Boolean).join(" · ") || "no confidence detail")}</div>`).join("")}` : ""}
    <div class="metadata-actions">
      ${disabledAction("Accept", "metadataBackend")}
      ${disabledAction("Reject", "metadataBackend")}
      ${disabledAction(t("saveMetadata"), "metadataBackend")}
    </div>
    ${commandPanel("Enrich with CLI", ["uv run manola enrich <meeting-id-or-path>"])}
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

function disabledWorkflowPanel(m) {
  const commands = [
    `uv run manola enrich ${m.id}`,
    `uv run manola export ${m.id} --share all`,
    `uv run manola transcribe ${m.id} --force --summarize`,
    `uv run manola summarize ${m.id} --force`,
  ];
  return `<div class="panel">
    <h2>Unsupported UI actions</h2>
    <p class="muted">These workflows are available through the CLI where noted, but need async jobs, write endpoints, and failure reporting before the browser UI can run them.</p>
    <div class="metadata-actions">
      ${disabledAction(t("enrichMetadata"), "metadataBackend")}
      ${disabledAction(t("exportMeeting"), "exportBackend")}
      ${disabledAction(t("repairAudio"), "repairBackend")}
      ${disabledAction(t("retranscribe"), "transcribeBackend")}
      ${disabledAction(t("regenerateReport"), "reportBackend")}
    </div>
    ${commandPanel("Workflow CLI commands", commands)}
  </div>`;
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
