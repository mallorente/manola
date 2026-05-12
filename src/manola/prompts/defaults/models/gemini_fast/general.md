COSTAR prompt.

Context:
This is a meeting transcript. It may contain transcription errors, speaker ambiguity, repeated phrases, or mixed Spanish/English.

Objective:
Create a useful Markdown meeting report that helps the owner quickly understand what happened and what needs follow-up.

Style:
Dense but readable. Prefer short bullets and concrete nouns.

Tone:
Neutral, professional, no hype.

Audience:
The meeting owner and people who need the decisions and next actions.

Response:
- Use the required sections exactly.
- Do not add an extra wrapper title.
- Keep each bullet grounded in transcript evidence.
- For missing owners/deadlines, say "Owner unclear" or "No deadline stated".

Meeting metadata:
- Title: {{title}}
- Type: {{meeting_type}}
- Project: {{project}}
- Language: {{language}}
- Attendees: {{attendees}}
- LLM profile: {{model_profile}}
- LLM model: {{model_name}}

Required sections:
{{sections}}

Transcript:
{{transcript}}
