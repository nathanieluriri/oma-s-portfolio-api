import json
from typing import Any, Dict, List

from api.v1 import portfolio as portfolio_api
from schemas.portfolio import PortfolioOut
from schemas.portfolio_suggestions import ApplySuggestionItem, ApplySuggestionsRequest
from services.portfolio_normalization import normalize_portfolio_doc
from services.portfolio_service import build_empty_portfolio_schema


TEST_PAYLOAD = {
    "updates": [
        {"field": "hero.name", "value": "Nathaniel Elo-Oghene Uriri", "expectedCurrent": ""},
        {
            "field": "contacts[0]",
            "value": "{\"label\":\"Email\",\"value\":\"nat@uriri.com.ng\",\"href\":\"mailto:nat@uriri.com.ng\"}",
            "expectedCurrent": "",
        },
        {
            "field": "contacts[1]",
            "value": "{\"label\":\"Phone\",\"value\":\"+2348053964826\",\"href\":\"tel:+2348053964826\"}",
            "expectedCurrent": "",
        },
        {
            "field": "contacts[2]",
            "value": "{\"label\":\"LinkedIn\",\"value\":\"Nathaniel uriri\",\"href\":\"https://www.linkedin.com/in/nathaniel-uriri\"}",
            "expectedCurrent": "",
        },
        {
            "field": "contacts[3]",
            "value": "{\"label\":\"GitHub\",\"value\":\"nathanieluriri\",\"href\":\"https://github.com/nathanieluriri\"}",
            "expectedCurrent": "",
        },
        {"field": "resumeUrl", "value": "https://example.com/resume.pdf", "expectedCurrent": ""},
        {"field": "experience[0].role", "value": "Head of Product & Innovation", "expectedCurrent": ""},
        {"field": "experience[0].organization", "value": "Digital Guardians", "expectedCurrent": ""},
        {"field": "experience[0].location", "value": "Abuja, Nigeria", "expectedCurrent": ""},
        {
            "field": "experience[1].role",
            "value": "Lead Mobile Developer & Product Designer",
            "expectedCurrent": "",
        },
        {"field": "experience[1].organization", "value": "Streamz", "expectedCurrent": ""},
        {"field": "experience[1].location", "value": "Abuja, Nigeria", "expectedCurrent": ""},
        {"field": "projects[0].name", "value": "Doux landing page", "expectedCurrent": ""},
        {"field": "projects[0].location", "value": "Abuja, Nigeria", "expectedCurrent": ""},
        {
            "field": "projects[0].description",
            "value": (
                "Contributed to the design of a high-impact landing page for Doux, a crypto spending solution, "
                "working closely with more experienced designers to refine concepts and improve design quality."
            ),
            "expectedCurrent": "",
        },
        {"field": "contacts[0].label", "value": "Email", "expectedCurrent": ""},
        {"field": "contacts[0].value", "value": "nat@uriri.com.ng", "expectedCurrent": ""},
        {"field": "contacts[0].href", "value": "mailto:nat@uriri.com.ng", "expectedCurrent": ""},
        {"field": "contacts[0].icon", "value": "email", "expectedCurrent": ""},
        {"field": "contacts[1].label", "value": "Phone", "expectedCurrent": ""},
        {"field": "contacts[1].value", "value": "+234 (805)-396-4826", "expectedCurrent": ""},
        {"field": "contacts[1].href", "value": "tel:+234 (805)-396-4826", "expectedCurrent": ""},
        {"field": "contacts[1].icon", "value": "phone", "expectedCurrent": ""},
    ]
}


def _set_value_at_path(data: Dict[str, Any], path: str, value: Any) -> None:
    tokens = portfolio_api._path_to_tokens(path)
    current: Any = data
    for idx, token in enumerate(tokens):
        is_last = idx == len(tokens) - 1
        if isinstance(token, int):
            if not isinstance(current, list):
                current_list: List[Any] = []
                if isinstance(current, dict):
                    # If the parent is a dict, replace it with a list.
                    raise ValueError(f"Invalid list path at '{path}'")
                current = current_list
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
                current[token] = {}
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
