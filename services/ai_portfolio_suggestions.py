import json
import os
from typing import List

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
    return parsed.suggestions
