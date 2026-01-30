# Suggestion API – Quick Guide

## Overview
Generates AI-powered, schema-valid partial patches for any portfolio section/field. Input can be raw text, an uploaded document, or a previously uploaded resume.

**Endpoint**: `POST /v1/suggestions/generate`  
**Auth**: Bearer access token (member)  
**Consumes**: `multipart/form-data`  
**Produces**: `application/json`

## Form Fields
- `target_path` (required, string): Dot/bracket path, e.g. `hero.title`, `experience[0].role`, `projects[1].caseStudy.overview`.
- `text_input` (optional, string): Raw text/context.
- `file` (optional, file): PDF, DOCX, or TXT.
- `use_existing_resume` (optional, bool): `true` to reuse stored `resumeUrl` on the user’s portfolio. Ignored if `file` or `text_input` is provided.

Priority for content extraction: `text_input` → `file` → `use_existing_resume`.

## Successful Response Shape
```json
{
  "status_code": 200,
  "detail": "Suggestion generated",
  "data": {
    "target": "hero.title",
    "patch": {
      "hero": { "title": "Senior Systems Engineer" }
    },
    "source_length": 12456
  }
}
```

## Error Responses (examples)
- `400`: validation issues (missing target_path, unsupported file type, no resume to reuse, AI JSON validation failure).
- `401/403`: auth or account status failures.
- `502`: upstream AI error.

## Example Calls

### 1) Simple text input (update hero title)
```bash
curl -X POST https://api.yourdomain.com/v1/suggestions/generate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "target_path=hero.title" \
  -F "text_input=I am Jane Doe, a senior systems engineer specializing in distributed systems."
```

### 2) PDF upload to populate experience[0]
```bash
curl -X POST https://api.yourdomain.com/v1/suggestions/generate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "target_path=experience[0]" \
  -F "file=@/path/to/resume.pdf;type=application/pdf"
```

Example success:
```json
{
  "status_code": 200,
  "detail": "Suggestion generated",
  "data": {
    "target": "experience[0]",
    "patch": {
      "experience": [
        {
          "date": "2022 — Present",
          "role": "Backend Engineer",
          "company": "Acme Corp",
          "description": "Owns messaging platform reliability.",
          "highlights": [
            "Cut p99 latency by 35%.",
            "Led migration to event-driven architecture."
          ],
          "current": true
        }
      ]
    },
    "source_length": 8421
  }
}
```

### 3) Reuse existing resume on file
```bash
curl -X POST https://api.yourdomain.com/v1/suggestions/generate \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "target_path=projects[0]" \
  -F "use_existing_resume=true"
```

## AI Response Formatting (server-side)
The backend already handles response formatting for the AI provider:

- **Primary mode**: `response_format={"type": "json_schema", "json_schema": {"name": "portfolio_patch", "schema": <pydantic-json-schema>, "strict": true}}`
- **Fallback** (for non-supporting models): `response_format={"type": "json_object"}`

Clients do **not** need to set these; they’re documented here for completeness and debugging.

## Notes & Limits
- Text is truncated to ~15,000 characters before sending to AI.
- Output is validated against the portfolio schema; only fields present in the text are returned.
- For list targets, the service returns the most relevant single item unless the AI supplies a full list that passes validation.
