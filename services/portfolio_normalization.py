from typing import Any, Dict, List


def _slugify(value: str) -> str:
    clean = "".join(char if char.isalnum() else "-" for char in value.lower())
    while "--" in clean:
        clean = clean.replace("--", "-")
    return clean.strip("-")


def normalize_contact_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    label = entry.get("label")
    value = entry.get("value")
    href = entry.get("href")
    method = entry.get("method")

    if not label and method:
        label = str(method).strip().title()
    if not href and value:
        if label and label.lower() == "email":
            href = f"mailto:{value}"
        elif label and label.lower() == "phone":
            href = f"tel:{value}"
        else:
            href = value
    return {
        "label": label or "",
        "value": value or "",
        "href": href or "",
        "icon": entry.get("icon"),
    }


def normalize_experience_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "date": entry.get("date") or entry.get("duration") or "",
        "role": entry.get("role") or "",
        "company": entry.get("company") or "",
        "link": entry.get("link"),
        "description": entry.get("description") or entry.get("location"),
        "highlights": entry.get("highlights") or entry.get("responsibilities") or [],
        "current": entry.get("current", False),
    }


def normalize_project_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    title = entry.get("title") or ""
    link = entry.get("link") or entry.get("url")
    if not link and title:
        link = f"/projects/{_slugify(title)}"
    role_title = entry.get("role") or ""
    achievements = entry.get("achievements") or entry.get("outcomes") or []
    technologies = entry.get("technologies") or entry.get("tags") or []
    return {
        "title": title,
        "tags": technologies,
        "description": entry.get("description") or "",
        "link": link or "",
        "caseStudy": {
            "overview": entry.get("overview") or "",
            "goal": entry.get("goal") or "",
            "role": {"title": role_title or "Full-Stack Engineer", "bullets": []},
            "screenshots": entry.get("screenshots") or [],
            "outcomes": achievements,
        },
    }


def normalize_skill_group(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": entry.get("title") or entry.get("category") or "",
        "items": entry.get("items") or entry.get("skills") or [],
    }


def normalize_update(field: str, value: Any) -> Any:
    if field == "contacts" and isinstance(value, list):
        return [normalize_contact_entry(item) for item in value]
    if field == "experience" and isinstance(value, list):
        return [normalize_experience_entry(item) for item in value]
    if field == "projects" and isinstance(value, list):
        return [normalize_project_entry(item) for item in value]
    if field == "skillGroups" and isinstance(value, list):
        return [normalize_skill_group(item) for item in value]
    return value


def normalize_portfolio_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    updates: Dict[str, Any] = {}
    if isinstance(doc.get("contacts"), list):
        updates["contacts"] = [normalize_contact_entry(item) for item in doc["contacts"]]
    if isinstance(doc.get("experience"), list):
        updates["experience"] = [normalize_experience_entry(item) for item in doc["experience"]]
    if isinstance(doc.get("projects"), list):
        updates["projects"] = [normalize_project_entry(item) for item in doc["projects"]]
    if isinstance(doc.get("skillGroups"), list):
        updates["skillGroups"] = [normalize_skill_group(item) for item in doc["skillGroups"]]
    return updates
