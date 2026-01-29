import json
import os
import re
import uuid
from typing import Dict, List, Optional

from openai import OpenAI

from schemas.portfolio_suggestions import PortfolioSuggestion, PortfolioSuggestionList


_SUGGESTION_SCHEMA = {
    "name": "portfolio_suggestions",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["suggestions"],
        "properties": {
            "suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "id",
                        "field",
                        "currentValue",
                        "suggestedValue",
                        "reasoning",
                        "confidence",
                    ],
                    "properties": {
                        "id": {"type": "string"},
                        "field": {"type": "string"},
                        "currentValue": {"type": "string"},
                        "suggestedValue": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            }
        },
    },
}


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars]


def _get_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06")


def _get_limits() -> tuple[int, int]:
    doc_limit = int(os.getenv("OPENAI_MAX_DOCUMENT_CHARS", "20000"))
    portfolio_limit = int(os.getenv("OPENAI_MAX_PORTFOLIO_CHARS", "20000"))
    return doc_limit, portfolio_limit


def _supports_json_schema(model: str) -> bool:
    return model.startswith("gpt-4o-2024-08-06") or model.startswith("gpt-4o-mini")


_EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/([A-Z0-9-]+)", re.IGNORECASE)
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/([A-Z0-9-_%]+)", re.IGNORECASE)
_X_RE = re.compile(r"(?:https?://)?(?:www\.)?(?:x\.com|twitter\.com)/([A-Z0-9_]+)", re.IGNORECASE)
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


def _first_match(pattern: re.Pattern, text: str) -> Optional[str]:
    match = pattern.search(text)
    if not match:
        return None
    if match.lastindex:
        return match.group(1)
    return match.group(0)


def _extract_contact_targets(document_text: str) -> List[Dict[str, str]]:
    targets: List[Dict[str, str]] = []
    email = _first_match(_EMAIL_RE, document_text)
    if email:
        targets.append(
            {"label": "Email", "value": email, "href": f"mailto:{email}", "icon": "email"}
        )
    github = _first_match(_GITHUB_RE, document_text)
    if github:
        targets.append(
            {
                "label": "GitHub",
                "value": f"github.com/{github}",
                "href": f"https://github.com/{github}",
                "icon": "github",
            }
        )
    linkedin = _first_match(_LINKEDIN_RE, document_text)
    if linkedin:
        targets.append(
            {
                "label": "LinkedIn",
                "value": f"linkedin.com/in/{linkedin}",
                "href": f"https://linkedin.com/in/{linkedin}",
                "icon": "linkedin",
            }
        )
    x_handle = _first_match(_X_RE, document_text)
    if x_handle:
        targets.append(
            {"label": "X", "value": f"x.com/{x_handle}", "href": f"https://x.com/{x_handle}", "icon": "x"}
        )
    phone_match = _first_match(_PHONE_RE, document_text)
    if phone_match:
        normalized_phone = " ".join(phone_match.split())
        targets.append(
            {
                "label": "Phone",
                "value": normalized_phone,
                "href": f"tel:{normalized_phone}",
                "icon": "phone",
            }
        )
    return targets


def _suggestion_exists(suggestions: List[PortfolioSuggestion], field: str) -> bool:
    return any(item.field == field for item in suggestions)


def _get_contact_index(contacts: List[Dict[str, str]], label: str, next_index: int) -> int:
    for idx, entry in enumerate(contacts):
        if str(entry.get("label", "")).strip().lower() == label.strip().lower():
            return idx
    return next_index


def _add_contact_supplements(
    suggestions: List[PortfolioSuggestion],
    current_portfolio: dict,
    document_text: str,
) -> List[PortfolioSuggestion]:
    contacts = current_portfolio.get("contacts") if isinstance(current_portfolio, dict) else None
    if not isinstance(contacts, list):
        contacts = []
    targets = _extract_contact_targets(document_text)
    if not targets:
        return suggestions

    next_index = len(contacts)
    for target in targets:
        index = _get_contact_index(contacts, target["label"], next_index)
        if index == next_index:
            next_index += 1

        for field_key in ("label", "value", "href", "icon"):
            field_path = f"contacts[{index}].{field_key}"
            if _suggestion_exists(suggestions, field_path):
                continue
            current_value = ""
            if index < len(contacts) and isinstance(contacts[index], dict):
                current_value = str(contacts[index].get(field_key) or "")
            suggested_value = target.get(field_key, "")
            if not suggested_value or current_value == suggested_value:
                continue
            suggestions.append(
                PortfolioSuggestion(
                    id=f"logic-contact-{uuid.uuid4().hex}",
                    field=field_path,
                    currentValue=current_value,
                    suggestedValue=suggested_value,
                    reasoning="Normalized contact data from the source document.",
                    confidence=0.72,
                )
            )
    return suggestions


def generate_portfolio_suggestions(document_text: str, current_portfolio: dict) -> List[PortfolioSuggestion]:
    doc_limit, portfolio_limit = _get_limits()
    document_text = _truncate(document_text, doc_limit)
    portfolio_json = _truncate(json.dumps(current_portfolio, ensure_ascii=True), portfolio_limit)

    client = OpenAI()
    system_prompt = (
        "You are an expert portfolio editor. Compare the current portfolio JSON with the "
        "new source document text. Suggest only concrete, document-supported improvements. "
        "If there is no clear improvement, return an empty suggestions array. "
        "Use dot-paths with array indices like projects[0].description for fields. "
        "When suggesting contacts, include label, value, href, and icon where available. "
        "Return JSON that matches the schema."
    )
    user_prompt = (
        f"Current Portfolio JSON:\n{portfolio_json}\n\n"
        f"New Source Document:\n{document_text}"
    )

    model = _get_model()
    response_format = {"type": "json_object"}
    if _supports_json_schema(model):
        response_format = {"type": "json_schema", "json_schema": _SUGGESTION_SCHEMA}

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_format,
    )

    content = response.choices[0].message.content or "{}"
    parsed = PortfolioSuggestionList.model_validate_json(content)
    supplemented = _add_contact_supplements(parsed.suggestions, current_portfolio, document_text)
    return supplemented
