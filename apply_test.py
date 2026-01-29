import json
from typing import Any, Dict, List

from api.v1 import portfolio as portfolio_api
from schemas.portfolio import PortfolioOut
from schemas.portfolio_suggestions import ApplySuggestionItem, ApplySuggestionsRequest
from services.portfolio_normalization import normalize_portfolio_doc
from services.portfolio_service import build_empty_portfolio_schema


TEST_PAYLOAD = {
    "updates": [
        {
            "field": "education[0].degree",
            "value": "B.Sc. in Computer Science, 2nd class upper",
            "expectedCurrent": "not present",
        },
        {"field": "education[0].institution", "value": "Veritas University", "expectedCurrent": "not present"},
        {"field": "education[0].location", "value": "Abuja, Nigeria", "expectedCurrent": "not present"},
        {"field": "education[0].graduationDate", "value": "August 2024", "expectedCurrent": "not present"},
        {"field": "education[0].gpa", "value": "4.36/5.00", "expectedCurrent": "not present"},
        {"field": "contacts[0].href", "value": "nat@uriri.com.ng", "expectedCurrent": "mailto:nat@uriri.com.ng"},
        {
            "field": "experience[0].description",
            "value": (
                "Docker, Nginx, Certbot, Linux Server Management, CI/CD, DevOps (Docker Compose). "
                "Led the end-to-end deployment of a government web application for Kogi State, ensuring secure, "
                "reliable, and scalable infrastructure. Configured Nginx as a reverse proxy to efficiently manage "
                "traffic routing and improve application performance. Containerised and deployed all application "
                "services using Docker Compose, enabling consistent environment replication and simplified updates. "
                "Monitored server performance and uptime, applying proactive maintenance and optimisation to ensure "
                "uninterrupted public access."
            ),
            "expectedCurrent": (
                "Docker, Nginx, Certbot, Linux Server Management, CI/CD, DevOps (Docker Compose). "
                "Led the end-to-end deployment of a government web application, ensuring secure, reliable, and "
                "scalable infrastructure. Configured Nginx as a reverse proxy and containerised services using "
                "Docker Compose."
            ),
        },
        {"field": "experience[1].date", "value": "May 2025 \u2013 Present", "expectedCurrent": ""},
        {
            "field": "projects[0].description",
            "value": (
                "Contributed to the design of a high-impact landing page for Doux, a crypto spending solution, "
                "working closely with more experienced designers to refine concepts and improve design quality."
            ),
            "expectedCurrent": "Contributed to the design of a high-impact landing page for Doux.",
        },
        {"field": "contacts[1].href", "value": "tel:+234 (805)-396-4826", "expectedCurrent": "tel:+2348053964826"},
    ]
}


def _set_value_at_path(data: Dict[str, Any], path: str, value: Any) -> None:
    tokens = portfolio_api._path_to_tokens(path)
    current: Any = data
    for idx, token in enumerate(tokens):
        is_last = idx == len(tokens) - 1
        if isinstance(token, int):
            if not isinstance(current, list):
                raise ValueError(f"Invalid list path at '{path}'")
            while len(current) <= token:
                current.append({})
            if is_last:
                current[token] = value
                return
            if not isinstance(current[token], (dict, list)):
                current[token] = {}
            current = current[token]
        else:
            if not isinstance(current, dict):
                raise ValueError(f"Invalid object path at '{path}'")
            if is_last:
                current[token] = value
                return
            if token not in current or not isinstance(current[token], (dict, list)):
                next_token = tokens[idx + 1]
                current[token] = [] if isinstance(next_token, int) else {}
            current = current[token]


def _map_field_aliases(field: str) -> str:
    if field.endswith(".organization"):
        return field.replace(".organization", ".company")
    if field.endswith(".position"):
        return field.replace(".position", ".role")
    if field.endswith(".name") and field.startswith("projects["):
        return field.replace(".name", ".title")
    return field


def apply_updates_in_memory(payload: Dict[str, Any]) -> PortfolioOut:
    parsed = ApplySuggestionsRequest.model_validate(payload)

    updates = portfolio_api._expand_contact_legacy_updates(parsed.updates)
    updates = portfolio_api._prune_root_updates_with_children(updates)
    updates = portfolio_api._prune_parent_index_updates(updates)

    data = build_empty_portfolio_schema("test-user")

    for item in updates:
        item.value = portfolio_api._maybe_parse_json(item.value)
        item.value = portfolio_api._coerce_list_field(item.field, item.value)
        normalized_value = portfolio_api.normalize_update(item.field, item.value)
        field = _map_field_aliases(item.field)
        _set_value_at_path(data, field, normalized_value)

    normalized_updates = normalize_portfolio_doc(data)
    for key, value in normalized_updates.items():
        data[key] = value

    return PortfolioOut(**data)


def main() -> None:
    portfolio = apply_updates_in_memory(TEST_PAYLOAD)
    print("Apply test passed")
    print(json.dumps(portfolio.model_dump(), indent=2))


if __name__ == "__main__":
    main()
