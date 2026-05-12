Analyze this meeting transcript and return only valid JSON.

Do not wrap the JSON in Markdown. Do not include commentary outside the JSON.

Existing metadata:
- Title: {{title}}
- Type: {{meeting_type}}
- Project: {{project}}
- Language: {{language}}
- Attendees: {{attendees}}

Return this JSON shape:

{
  "suggested_title": "short human-readable title or null",
  "suggested_meeting_type": "one of general, sales_discovery, sales_demo, customer_success, client_update, internal_sync, one_on_one, job_interview, case_interview, project_review, incident_postmortem, brainstorm, strategy, workshop, refinement, daily, retro, planning, or null",
  "suggested_project": "project name or null",
  "suggested_attendees": ["names inferred from evidence"],
  "notable_terms": ["recurring product, company, project, or domain terms"],
  "possible_name_corrections": [
    {
      "heard_as": "misrecognized transcript text",
      "suggested": "likely correct term",
      "confidence": "low, medium, or high",
      "evidence": "short reason from transcript"
    }
  ],
  "summary": "brief summary of what this meeting is about",
  "confidence_notes": ["short notes about uncertainty or evidence quality"]
}

Rules:
- Prefer null or empty arrays when evidence is weak.
- Do not invent attendees, projects, or corrections.
- Keep suggested_title concise.
- Preserve the transcript language when possible.

Transcript:
{{transcript}}
