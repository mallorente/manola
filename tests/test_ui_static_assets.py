from __future__ import annotations

from pathlib import Path


STATIC_DIR = Path(__file__).resolve().parents[1] / "src" / "manola" / "ui_static"


def test_sidebar_uses_svg_icons_for_primary_navigation():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    sidebar = html.split('<aside class="sidebar">', 1)[1].split("</aside>", 1)[0]
    nav_buttons = [
        'id="recordButton"',
        'data-view="archive"',
        'data-view="attention"',
        'data-view="import"',
        'data-view="devices"',
        'data-view="doctor"',
        'data-view="settings"',
    ]

    for marker in nav_buttons:
        button = sidebar.split(marker, 1)[1].split("</button>", 1)[0]
        assert '<svg class="icon"' in button

    assert '<span class="icon">' not in sidebar


def test_attention_filter_has_distinct_sidebar_active_state():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "function activeNavView()" in js
    assert 'state.filter === "attention" ? "attention" : state.view' in js
    assert 'btn.dataset.view === activeNavView()' in js


def test_sidebar_theme_toggle_is_icon_button_and_has_no_language_selector():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    sidebar = html.split('<aside class="sidebar">', 1)[1].split("</aside>", 1)[0]
    theme_button = sidebar.split('id="themeToggle"', 1)[1].split("</button>", 1)[0]

    assert '<svg class="icon"' in theme_button
    assert 'id="appLanguage"' not in sidebar
    assert 'data-i18n="appLanguage"' not in sidebar


def test_archive_groups_meetings_by_day_and_shows_share_badge():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "function groupMeetingsByDay(meetings)" in js
    assert 'heading.className = "meeting-day"' in js
    assert 'groupMeetingsByDay(meetings).forEach((group)' in js
    assert 'class="badge share"' in js
    assert "function shareLabel(policy)" in js
    assert 'share: private' in js


def test_archive_has_fallback_title_and_clear_selected_row_style():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "function meetingTitle(meeting)" in js
    assert "Untitled meeting" in js
    assert "${escapeHtml(meetingTitle(m))}" in js
    assert ".meeting-row.selected {" in css
    assert "box-shadow: inset 3px 0 0 var(--accent), var(--shadow);" in css


def test_archive_supports_selectable_sorting_persisted_in_localstorage():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert 'id="meetingSort"' in html
    assert 'id="meetingSortDir"' in html
    for value in ('value="date"', 'value="title"', 'value="type"', 'value="duration"'):
        assert value in html

    assert 'localStorage.getItem("manola.sortKey")' in js
    assert 'localStorage.getItem("manola.sortDir")' in js
    assert 'localStorage.setItem("manola.sortKey", state.sortKey)' in js
    assert 'localStorage.setItem("manola.sortDir", state.sortDir)' in js
    assert "function sortMeetings(meetings)" in js
    assert "function compareMeetings(a, b, key)" in js
    assert "sortMeetings(filteredMeetings())" in js
    # date grouping is still applied after sorting
    assert "groupMeetingsByDay(meetings).forEach((group)" in js
    assert ".sort-bar" in css


def test_report_tab_renders_sections_and_backend_gap_states():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "function renderMarkdownSections(text)" in js
    assert "function markdownSections(text)" in js
    assert "function markdownLines(lines)" in js
    assert 'class="report-section"' in js
    assert 'class="panel report-context"' in js
    assert 't("regenerateReport")' in js
    assert 't("noReport")' in js
    assert 't("noReportSub")' in js
    assert 'm.report_stale ? `<div class="panel warn">${t("reportStale")}' in js
    assert ".report-sections" in css
    assert ".report-context" in css


def test_transcript_tab_supports_speakers_metadata_and_retranscribe_gap():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "const timestamped = line.match" in js
    assert "const speaker = body.match" in js
    assert "speaker?.[1]" in js
    assert "m.transcription_model" in js
    assert "m.transcription_device" in js
    assert "m.transcription_compute_type" in js
    assert 'm.health.transcript_mismatch ? `<div class="panel warn">' in js
    assert 't("retranscribe")' in js
    assert 't("noTranscript")' in js
    assert 'class="speaker"' in js
    assert ".speaker" in css


def test_audio_tab_lists_artifacts_warnings_and_repair_gap():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "function renderAudioTab(body, m)" in js
    assert 't("sourceAudio")' in js
    assert 't("normalizedAudio")' in js
    assert 'm.health.normalized_mismatch ? `<div class="panel warn">' in js
    assert 't("missingAudio")' in js
    assert 't("repairAudio")' in js
    assert "function audioArtifact(label, artifact)" in js
    assert '["Duration", artifact.duration_label || "unknown"]' in js
    assert "function formatBytes(value)" in js
    assert ".audio-artifact" in css
    assert ".audio-path" in css


def test_metadata_tab_enriches_and_applies_suggestions():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "function renderMetadata(body, m)" in js
    assert '["Attendees", (m.attendees || []).join(", ")]' in js
    assert '["LLM profile", m.llm_profile]' in js
    # Enrich runs as a privacy-gated job; suggestions can be applied per field.
    assert 'document.getElementById("enrichBtn")' in js
    assert '"enrich"' in js
    assert "function metadataSuggestions(suggestions)" in js
    assert "suggestions.suggested_title" in js
    assert "suggestions.possible_name_corrections" in js
    assert "function applySuggestion(m, updates, mount)" in js
    assert 'apiPost("/api/meeting/apply"' in js
    assert "function bindMetadataApply(m)" in js
    assert '"applyTitle"' in js
    assert "function metadataValue(value)" in js
    assert "none</span>" in js
    assert ".metadata-actions" in css


def test_settings_has_editable_whitelisted_fields_and_read_only_config():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert 'localStorage.getItem("manola.appLanguage")' in js
    assert 'localStorage.setItem("manola.appLanguage", state.lang)' in js
    assert 'localStorage.getItem("manola.highlightColor")' in js
    assert 'id="appLanguage"' in html
    assert 'id="highlightColor"' in html
    assert 't("backendConfig")' in js
    assert 't("backendConfigSub")' in js
    # Whitelisted fields are editable and persisted via POST /api/config.
    assert "function settingControl(field, label, kind, value, options)" in js
    assert "function saveConfig(field, value, mount)" in js
    assert 'apiPost("/api/config"' in js
    assert '"workspace_dir"' in js
    assert '"default_llm_profile"' in js
    assert '"local_whisper_device"' in js
    # Non-editable backend values remain read-only.
    assert 'aria-readonly="true"' in js
    assert ".readonly-value" in css


def test_devices_tab_selects_and_saves_capture_devices():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "function renderDevices()" in js
    assert "report.microphones" in js
    assert "report.speakers" in js
    assert "report.loopbacks" in js
    # Mic/speaker pickers persist default_mic_index / default_speaker_index.
    assert "function deviceSelect(id, devices, selectedIndex)" in js
    assert "function bindDeviceSave()" in js
    assert 't("saveDevices")' in js
    assert "default_mic_index" in js
    assert "default_speaker_index" in js
    assert 'apiPost("/api/config", { default_mic_index: mic, default_speaker_index: spk })' in js
    # Doctor stays a read-only CLI surface (out of Batch 3 scope).
    assert "function renderDoctor()" in js
    assert 't("rerunDoctor")' in js
    assert "uv run manola doctor" in js
    assert "function commandPanel(title, commands)" in js
    assert ".command-panel" in css
    assert ".control-group" in css


def test_record_screen_starts_and_stops_recording():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "function renderRecord()" in js
    assert "function bindRecord()" in js
    # Start/stop drive the recording job + stop endpoint.
    assert 'apiPost("/api/jobs/record"' in js
    assert 'apiPost("/api/recording/stop", { job_id: state.recordingJobId })' in js
    assert 't("startRecording")' in js
    assert 't("stopRecording")' in js
    assert 'id="recStartBtn"' in js
    assert 'id="recStopBtn"' in js
    assert "state.recordingJobId" in js
    assert "MEETING_TYPES" in js
    assert "config.default_mic_index" in js
    # On completion the new meeting is refreshed and selected.
    assert "state.selectedPath = result.meeting" in js


def test_import_screen_is_complete_but_inert():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "function renderImport()" in js
    assert "Browser import needs a file upload endpoint or desktop file-picker handoff" in js
    assert 't("chooseAudio")' in js
    assert 't("processImport")' in js
    assert "Meeting metadata" in js
    assert "config.default_language" in js
    assert "Share policy" in js
    assert "Meetings/YYYY-MM-DD__general__imported-audio" in js
    assert "function importPipelineRows()" in js
    assert '"Copy original", "Normalize", "Transcribe", "Summarize", "Export"' in js
    assert "uv run manola import <audio-path> --language en" in js
    assert "uv run manola process <audio-path> --language es --share all" in js


def test_reusable_job_component_wires_retranscribe():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    # The reusable async-job component (ADR-0003) Batch 3 actions will reuse.
    assert "async function runJob(action, params, mount" in js
    assert "async function pollJob(jobId, mount, onDone)" in js
    assert "function renderJobStatus(mount, job)" in js
    assert "body.confirm_remote_llm = true" in js
    assert "async function refreshMeeting(path)" in js

    # Retranscribe is wired end-to-end through the job API (tracer bullet).
    assert "function bindRetranscribe(m)" in js
    assert 'runJob("transcribe", { meeting: m.path, force: true }' in js
    assert 'id="retranscribeBtn"' in js
    assert 'id="retranscribeJob"' in js
    assert ".job-status" in css
    assert ".spinner" in css


def test_batch3_actions_are_wired_through_the_job_api():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    # Shared helpers used by every Batch 3 action.
    assert "function wireJobButton(btn, mount, action, params" in js
    assert "function confirmRemoteLlm()" in js
    assert 't("privacyConfirm")' in js

    # Overview "Actions" panel replaces the old disabled CLI-fallback panel.
    assert "function actionsPanel(m)" in js
    assert "function bindActionsPanel(m)" in js
    assert "function disabledWorkflowPanel(m)" not in js

    # Regenerate report (#32) is a privacy-gated summarize job.
    assert 'id="regenerateBtn"' in js
    assert '"summarize"' in js
    assert "needsConfirm: true" in js
    # Repair (#37) is wired as a job.
    assert 'id="repairBtn"' in js
    assert '"repair"' in js
    # Export (#34) with a share-policy picker.
    assert 'id="exportPolicy"' in js
    assert '"export"' in js
    assert 't("policyReportTranscript")' in js
    assert "confidence: ${item.confidence}" in js
    assert "evidence: ${item.evidence}" in js
