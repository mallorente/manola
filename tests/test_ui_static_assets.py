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


def test_metadata_tab_is_read_only_and_shows_suggestions():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "function renderMetadata(body, m)" in js
    assert '["Attendees", (m.attendees || []).join(", ")]' in js
    assert '["LLM profile", m.llm_profile]' in js
    assert 't("metadataReadonly")' in js
    assert 't("saveMetadata")' in js
    assert "function metadataSuggestions(suggestions)" in js
    assert "suggestions.suggested_title" in js
    assert "suggestions.possible_name_corrections" in js
    assert 't("applySuggestions")' in js
    assert "function metadataValue(value)" in js
    assert "none</span>" in js
    assert ".metadata-actions" in css


def test_settings_distinguishes_browser_preferences_from_read_only_config():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert 'localStorage.getItem("manola.appLanguage")' in js
    assert 'localStorage.setItem("manola.appLanguage", state.lang)' in js
    assert 'localStorage.getItem("manola.highlightColor")' in js
    assert 'localStorage.setItem("manola.highlightColor", state.highlight)' in js
    assert 'id="appLanguage"' in html
    assert 'id="highlightColor"' in html
    assert 't("backendConfig")' in js
    assert 't("backendConfigSub")' in js
    assert '[t("sharing"),' in js
    assert '[t("prompts"),' in js
    assert 'config.prompts_dir' in js
    assert 'config.shared_dir || "not configured"' in js
    assert 'aria-readonly="true"' in js
    assert ".readonly-value" in css


def test_devices_and_doctor_show_cli_alternatives_and_disabled_actions():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "function renderDevices()" in js
    assert "report.microphones" in js
    assert "report.speakers" in js
    assert "report.loopbacks" in js
    assert 't("testDevices")' in js
    assert "uv run manola audio setup" in js
    assert "uv run manola audio test --source meeting --duration 10" in js
    assert "function renderDoctor()" in js
    assert 't("rerunDoctor")' in js
    assert "uv run manola doctor" in js
    assert "uv run manola audio doctor" in js
    assert "function commandPanel(title, commands)" in js
    assert ".command-panel" in css


def test_record_screen_is_complete_but_inert():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    css = (STATIC_DIR / "app.css").read_text(encoding="utf-8")

    assert "function renderRecord()" in js
    assert "Meeting defaults" in js
    assert "Capture defaults" in js
    assert "config.default_language" in js
    assert "config.default_mic_index" in js
    assert "config.default_speaker_index" in js
    assert 't("liveTranscript")' in js
    assert 't("startRecording")' in js
    assert 't("stopRecording")' in js
    assert 't("processRecording")' in js
    assert "recording job API plus live level/transcript events" in js
    assert "uv run manola meet --language en" in js
    assert ".static-meter" in css
    assert ".meter-row" in css


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


def test_enrich_and_disabled_action_flows_are_explicit():
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")

    assert "function disabledWorkflowPanel(m)" in js
    assert 't("enrichMetadata")' in js
    assert 't("exportMeeting")' in js
    assert 'disabledAction(t("repairAudio"), "repairBackend")' in js
    assert 'disabledAction(t("retranscribe"), "transcribeBackend")' in js
    assert 'disabledAction(t("regenerateReport"), "reportBackend")' in js
    assert "uv run manola enrich" in js
    assert "uv run manola export" in js
    assert "function backendGapDetail(area)" in js
    assert "Export needs an async backend job endpoint" in js
    assert "Metadata enrichment and apply/save need write endpoints" in js
    assert "confidence: ${item.confidence}" in js
    assert "evidence: ${item.evidence}" in js
    assert "Enrich with CLI" in js
