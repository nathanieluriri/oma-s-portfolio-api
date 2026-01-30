
from fastapi import APIRouter, HTTPException, Query, Path, status, Depends, BackgroundTasks, UploadFile, File
from typing import List, Optional
import json
import ast
import time
import uuid
import anyio
import mimetypes
import os
from schemas.response_schema import APIResponse
from schemas.tokens_schema import accessTokenOut
from schemas.portfolio import (
    PortfolioCreate,
    PortfolioOut,
    PortfolioBase,
    PortfolioUpdate,
)
from schemas.portfolio_suggestions import (
    AnalyzePortfolioResponse,
    ApplySuggestionsRequest,
    ApplySuggestionItem,
)
from security.auth import verify_token
from security.account_status_check import check_user_account_status_and_permissions
from services.r2_service import get_r2_settings, build_public_url, upload_pdf_bytes, upload_bytes
from services.portfolio_service import (
    add_portfolio,
    remove_portfolio_by_user_id,
    retrieve_portfolios,
    retrieve_portfolio_by_user_id,
    retrieve_portfolio_raw_by_user_id,
    update_portfolio_by_user_id,
    update_portfolio_fields_by_user_id,
    build_empty_portfolio_schema,
    build_empty_portfolio_create,
)
from services.revalidate_service import trigger_portfolio_revalidate
from services.document_service import process_portfolio_document
from services.ai_portfolio_suggestions import generate_portfolio_suggestions
from services.portfolio_normalization import (
    normalize_update,
    normalize_contact_entry,
    normalize_experience_entry,
    normalize_project_entry,
    normalize_skill_group,
)

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


ALLOWED_PORTFOLIO_PREFIXES = {
    "navItems",
    "footer",
    "hero",
    "experience",
    "projects",
    "skillGroups",
    "education",
    "contacts",
    "theme",
    "animations",
    "metadata",
    "resumeUrl",
}

_LIST_FIELDS = {"contacts", "experience", "projects", "skillGroups", "education"}
_LIST_LEAF_SUFFIXES = {".highlights", ".items", ".tags", ".bio", ".outcomes", ".screenshots"}


def _path_to_tokens(path: str) -> list:
    tokens = []
    buffer = ""
    idx = 0
    while idx < len(path):
        char = path[idx]
        if char == ".":
            if buffer:
                tokens.append(buffer)
                buffer = ""
            idx += 1
            continue
        if char == "[":
            if buffer:
                tokens.append(buffer)
                buffer = ""
            end = path.find("]", idx)
            if end == -1:
                raise ValueError("Invalid field path")
            index = path[idx + 1 : end]
            if not index.isdigit():
                raise ValueError("Invalid array index in field path")
            tokens.append(int(index))
            idx = end + 1
            continue
        buffer += char
        idx += 1
    if buffer:
        tokens.append(buffer)
    return tokens


def _field_path_to_mongo(path: str) -> str:
    tokens = _path_to_tokens(path)
    mongo_parts = []
    for token in tokens:
        if isinstance(token, int):
            mongo_parts.append(str(token))
        else:
            mongo_parts.append(token)
    return ".".join(mongo_parts)


def _read_value_at_path(data: dict, path: str):
    tokens = _path_to_tokens(path)
    current = data
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                return None
            current = current[token]
        else:
            if not isinstance(current, dict) or token not in current:
                return None
            current = current[token]
    return current


def _tokens_to_mongo(tokens: list) -> str:
    parts = []
    for token in tokens:
        parts.append(str(token) if isinstance(token, int) else token)
    return ".".join(parts)


def _append_push_updates(push_updates: dict, key: str, value):
    existing = push_updates.get(key)
    if not existing:
        push_updates[key] = value
        return
    if isinstance(existing, dict) and "$each" in existing:
        existing["$each"].append(value)
    else:
        push_updates[key] = {"$each": [existing, value]}


def _strip_url_prefix(value: str) -> str:
    trimmed = value.strip()
    if trimmed.startswith("http://"):
        return trimmed[7:]
    if trimmed.startswith("https://"):
        return trimmed[8:]
    if trimmed.startswith("www."):
        return trimmed[4:]
    return trimmed


def _resolve_image_extension(upload: UploadFile) -> str:
    ext = ""
    if upload.filename:
        _, ext = os.path.splitext(upload.filename)
    if not ext:
        guessed = mimetypes.guess_extension(upload.content_type or "")
        ext = guessed or ""
    if not ext:
        ext = ".img"
    return ext.lower()


def _ensure_image_upload(upload: UploadFile, field_label: str) -> None:
    if not upload.content_type or not upload.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_label} must be an image file",
        )


def _normalize_contact_legacy_value(kind: str, value: str) -> dict:
    cleaned = value.strip()
    if kind == "email":
        return {
            "label": "Email",
            "value": cleaned,
            "href": f"mailto:{cleaned}" if cleaned else "",
            "icon": "email",
        }
    if kind == "phone":
        return {
            "label": "Phone",
            "value": cleaned,
            "href": f"tel:{cleaned}" if cleaned else "",
            "icon": "phone",
        }
    if kind == "github":
        display = _strip_url_prefix(cleaned).replace("github.com/", "")
        handle = display.strip().strip("/")
        href = f"https://github.com/{handle}" if handle else ""
        return {
            "label": "GitHub",
            "value": f"github.com/{handle}" if handle else cleaned,
            "href": href,
            "icon": "github",
        }
    if kind == "linkedin":
        display = _strip_url_prefix(cleaned)
        if "linkedin.com" in display:
            href = f"https://{display}".replace("https://https://", "https://")
            value = display.replace("linkedin.com/in/", "").strip("/")
        else:
            handle = display.replace(" ", "-")
            href = f"https://linkedin.com/in/{handle}" if handle else ""
            value = handle or cleaned
        return {
            "label": "LinkedIn",
            "value": f"linkedin.com/in/{value}" if value else cleaned,
            "href": href,
            "icon": "linkedin",
        }
    if kind in {"x", "twitter"}:
        display = _strip_url_prefix(cleaned).replace("twitter.com/", "").replace("x.com/", "")
        handle = display.strip().lstrip("@")
        href = f"https://x.com/{handle}" if handle else ""
        return {
            "label": "X",
            "value": f"x.com/{handle}" if handle else cleaned,
            "href": href,
            "icon": "x",
        }
    return {"label": "", "value": cleaned, "href": "", "icon": None}


def _expand_contact_legacy_updates(updates: list[ApplySuggestionItem]) -> list[ApplySuggestionItem]:
    legacy_fields = {}
    existing_fields = {item.field for item in updates}
    expanded: list[ApplySuggestionItem] = []
    for item in updates:
        tokens = _path_to_tokens(item.field)
        if len(tokens) == 3 and tokens[0] == "contacts" and isinstance(tokens[1], int):
            key = str(tokens[2]).lower()
            if key in {"email", "phone", "linkedin", "github", "x", "twitter"}:
                legacy_fields[(tokens[1], key)] = item
                continue
        expanded.append(item)

    for (index, key), item in legacy_fields.items():
        normalized = _normalize_contact_legacy_value(key, str(item.value or ""))
        for field_key in ("label", "value", "href", "icon"):
            field_path = f"contacts[{index}].{field_key}"
            if field_path in existing_fields:
                continue
            expanded.append(
                ApplySuggestionItem(
                    field=field_path,
                    value=normalized.get(field_key),
                    expectedCurrent=item.expectedCurrent,
                )
            )
    return expanded


def _prune_root_updates_with_children(updates: list[ApplySuggestionItem]) -> list[ApplySuggestionItem]:
    roots_with_children: set[str] = set()
    root_updates: set[str] = set()
    for item in updates:
        tokens = _path_to_tokens(item.field)
        if not tokens:
            continue
        root = str(tokens[0])
        if len(tokens) == 1:
            root_updates.add(root)
        else:
            roots_with_children.add(root)
    if not roots_with_children:
        return updates
    pruned: list[ApplySuggestionItem] = []
    for item in updates:
        tokens = _path_to_tokens(item.field)
        if tokens and len(tokens) == 1 and tokens[0] in roots_with_children:
            continue
        pruned.append(item)
    return pruned


def _prune_parent_index_updates(updates: list[ApplySuggestionItem]) -> list[ApplySuggestionItem]:
    parent_index_fields: set[str] = set()
    for item in updates:
        tokens = _path_to_tokens(item.field)
        if len(tokens) == 2 and isinstance(tokens[1], int) and tokens[0] in _LIST_FIELDS:
            parent_index_fields.add(item.field)
    if not parent_index_fields:
        return updates
    pruned: list[ApplySuggestionItem] = []
    for item in updates:
        tokens = _path_to_tokens(item.field)
        if len(tokens) > 2 and isinstance(tokens[1], int) and tokens[0] in _LIST_FIELDS:
            if f"{tokens[0]}[{tokens[1]}]" in parent_index_fields:
                continue
        pruned.append(item)
    return pruned


def _set_nested_dict_value(target: dict, keys: list[str], value) -> None:
    current = target
    for idx, key in enumerate(keys):
        if idx == len(keys) - 1:
            current[key] = value
            return
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]


def _coalesce_indexed_children(updates: list[ApplySuggestionItem]) -> list[ApplySuggestionItem]:
    parent_fields: set[str] = set()
    for item in updates:
        tokens = _path_to_tokens(item.field)
        if len(tokens) == 2 and isinstance(tokens[1], int) and tokens[0] in _LIST_FIELDS:
            parent_fields.add(item.field)

    grouped: dict[tuple[str, int], dict] = {}
    kept: list[ApplySuggestionItem] = []
    for item in updates:
        tokens = _path_to_tokens(item.field)
        if len(tokens) > 2 and isinstance(tokens[1], int) and tokens[0] in _LIST_FIELDS:
            parent_field = f"{tokens[0]}[{tokens[1]}]"
            if parent_field in parent_fields:
                continue
            key_list = [str(token) for token in tokens[2:]]
            group = grouped.setdefault((tokens[0], tokens[1]), {})
            _set_nested_dict_value(group, key_list, item.value)
            continue
        kept.append(item)

    for (root, index), value in grouped.items():
        kept.append(
            ApplySuggestionItem(
                field=f"{root}[{index}]",
                value=value,
                expectedCurrent="",
            )
        )
    return kept


def _apply_indexed_list_set(
    updates: dict,
    current_data: dict,
    field: str,
    value,
) -> bool:
    tokens = _path_to_tokens(field)
    if len(tokens) != 2 or not isinstance(tokens[1], int):
        return False
    root = tokens[0]
    index = tokens[1]
    if root not in _LIST_FIELDS:
        return False
    parent_value = _read_value_at_path(current_data, root)
    if isinstance(updates.get(root), list):
        items = updates[root]
        while len(items) <= index:
            items.append({})
        items[index] = value
        return True
    if not isinstance(parent_value, list):
        items = []
        while len(items) <= index:
            items.append({})
        items[index] = value
        updates[root] = items
        return True
    return False


def _validate_update_fields(paths: list[str]) -> None:
    for path in paths:
        if not path or not isinstance(path, str):
            raise ValueError("Invalid update field")
        base = path.split(".", 1)[0].split("[", 1)[0]
        if base not in ALLOWED_PORTFOLIO_PREFIXES:
            raise ValueError(f"Update field not allowed: {path}")


def _maybe_parse_json(value):
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.startswith("{") or trimmed.startswith("["):
            try:
                return json.loads(trimmed)
            except Exception:
                return value
    return value


def _coerce_list_field(field: str, value):
    if field not in _LIST_FIELDS:
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return []
        try:
            parsed = json.loads(trimmed)
        except Exception:
            start = trimmed.find("[")
            end = trimmed.rfind("]")
            if start != -1 and end != -1 and end > start:
                candidate = trimmed[start : end + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON list for field '{field}'",
            )
        return parsed
    return value


def _coerce_leaf_list_field(field: str, value):
    """Coerce stringified list payloads for nested list fields (e.g., experience[0].highlights)."""
    if not any(field.endswith(suffix) for suffix in _LIST_LEAF_SUFFIXES):
        return value
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return value
    trimmed = value.strip()
    if not trimmed:
        return []
    # First, try strict JSON.
    try:
        return json.loads(trimmed)
    except Exception:
        pass
    # Next, try Python literal (handles single quotes).
    try:
        parsed = ast.literal_eval(trimmed)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    # Finally, attempt to extract the bracketed portion and JSON-parse it.
    start = trimmed.find("[")
    end = trimmed.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidate = trimmed[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            try:
                parsed = ast.literal_eval(candidate)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid list for field '{field}'",
    )


def _map_field_aliases(field: str) -> str:
    if field.endswith(".organization"):
        return field.replace(".organization", ".company")
    if field.endswith(".position"):
        return field.replace(".position", ".role")
    if field.endswith(".name") and field.startswith("projects["):
        return field.replace(".name", ".title")
    return field


def _normalize_indexed_update(field: str, value):
    tokens = _path_to_tokens(field)
    if len(tokens) != 2 or not isinstance(tokens[1], int):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        value = value[0]
    if tokens[0] == "contacts" and isinstance(value, dict):
        return normalize_contact_entry(value)
    if tokens[0] == "experience" and isinstance(value, dict):
        return normalize_experience_entry(value)
    if tokens[0] == "projects" and isinstance(value, dict):
        return normalize_project_entry(value)
    if tokens[0] == "skillGroups" and isinstance(value, dict):
        return normalize_skill_group(value)
    return value


def _is_empty_value(value) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _values_equivalent(current, expected) -> bool:
    if _is_empty_value(current) and _is_empty_value(expected):
        return True
    return current == expected


def _can_append_missing_list_leaf(data: dict, tokens: list, expected_current) -> bool:
    if not tokens or _is_empty_value(expected_current) is False:
        return False
    index_positions = [idx for idx, token in enumerate(tokens) if isinstance(token, int)]
    if not index_positions:
        return False
    list_index_position = index_positions[-1]
    parent_tokens = tokens[:list_index_position]
    parent_value = _read_value_at_path(data, _tokens_to_mongo(parent_tokens))
    index = tokens[list_index_position]
    if parent_value is None:
        return index == 0
    return isinstance(parent_value, list) and index == len(parent_value)




async def _upload_resume_and_update(user_id: str, file_bytes: bytes, key: str, resume_url: str):
    await anyio.to_thread.run_sync(upload_pdf_bytes, file_bytes, key) # type: ignore
    await update_portfolio_by_user_id(portfolio_data=PortfolioUpdate(resumeUrl=resume_url), user_id=user_id)
    await trigger_portfolio_revalidate()

# ------------------------------
# Retrieve a single Portfolio
# ------------------------------
@router.get("/{user_id}", response_model=APIResponse[PortfolioOut])
async def get_portfolio_by_user_id(
    user_id: str = Path(..., description="user ID to fetch portfolio")
):
    """
    Retrieves a single Portfolio by its user ID.
    """
    item = await retrieve_portfolio_by_user_id(user_id=user_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Portfolio not found")
    return APIResponse(status_code=200, data=item, detail="portfolio item fetched")


# ------------------------------
# Create a new Portfolio
# ------------------------------
# Uses PortfolioBase for input (correctly)
@router.post(
    "/",
    response_model=APIResponse[PortfolioOut],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
)
async def create_portfolio(
    payload: PortfolioBase,
    background_tasks: BackgroundTasks,
    token: accessTokenOut = Depends(verify_token),
):
    """
    Creates a new Portfolio.
    """
    # Creates PortfolioCreate object which includes date_created/last_updated
    new_data = PortfolioCreate(**payload.model_dump(exclude={"user_id"}), user_id=token.userId)
    new_item = await add_portfolio(new_data, user_id=token.userId)
    if not new_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create portfolio")
    
    background_tasks.add_task(trigger_portfolio_revalidate)
    return APIResponse(status_code=201, data=new_item, detail=f"Portfolio created successfully")


# ------------------------------
# Update an existing Portfolio
# ------------------------------
# Uses PATCH for partial update (correctly)
@router.patch(
    "/",
    response_model=APIResponse[PortfolioOut],
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
)
async def update_portfolio(
    payload: PortfolioUpdate ,
    background_tasks: BackgroundTasks,
    token: accessTokenOut = Depends(verify_token),
):
    """
    Updates an existing Portfolio by its ID.
    Assumes the service layer handles partial updates (e.g., ignores None fields in payload).
    """
    updated_item = await update_portfolio_by_user_id(portfolio_data=payload, user_id=token.userId)
    if not updated_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Portfolio not found or update failed")
    
    background_tasks.add_task(trigger_portfolio_revalidate)
    return APIResponse(status_code=200, data=updated_item, detail=f"Portfolio updated successfully")


# ------------------------------
# Delete an existing Portfolio
# ------------------------------
@router.delete(
    "/",
    response_model=APIResponse[None],
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
)
async def delete_portfolio(
    background_tasks: BackgroundTasks,
    token: accessTokenOut = Depends(verify_token),
):
    """
    Deletes an existing Portfolio by its ID.
    """
    deleted = await remove_portfolio_by_user_id(user_id=token.userId)
    if not deleted:
        # This assumes remove_portfolio returns a boolean or similar
        # to indicate if deletion was successful (i.e., item was found).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Portfolio not found or deletion failed")
    
    background_tasks.add_task(trigger_portfolio_revalidate)
    return APIResponse(status_code=200, data=None, detail=f"Portfolio deleted successfully")


@router.post(
    "/upload_resume",
    response_model=APIResponse[dict],
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
)
async def upload_resume(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    token: accessTokenOut = Depends(verify_token),
):
    """
    Upload a resume PDF to Cloudflare R2 and update the portfolio resumeUrl.
    """
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed")
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content type")

    # Ensure the portfolio exists before scheduling the upload
    await retrieve_portfolio_by_user_id(user_id=token.userId)

    try:
        endpoint_url, _, _, bucket = get_r2_settings()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudflare R2 environment variables not configured",
        )

    file_bytes = await resume.read()
    key = f"resumes/{token.userId}/{uuid.uuid4().hex}.pdf"
    resume_url = build_public_url(endpoint_url, bucket, key)

    background_tasks.add_task(_upload_resume_and_update, token.userId, file_bytes, key, resume_url)

    return APIResponse(
        status_code=202,
        data={"resumeUrl": resume_url},
        detail="Resume upload queued",
    )


@router.post(
    "/upload_metadata_images",
    response_model=APIResponse[dict],
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
)
async def upload_metadata_images(
    background_tasks: BackgroundTasks,
    social_image: Optional[UploadFile] = File(None),
    anagram_dark: Optional[UploadFile] = File(None),
    anagram_light: Optional[UploadFile] = File(None),
    favicon: Optional[UploadFile] = File(None),
    token: accessTokenOut = Depends(verify_token),
):
    """
    Upload images to update portfolio metadata URLs (social image, anagrams, favicon).
    """
    uploads = {
        "socialImageUrl": social_image,
        "anagramDarkModeUrl": anagram_dark,
        "anagramLightModeUrl": anagram_light,
        "faviconImageUrl": favicon,
    }
    if not any(uploads.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one image file is required",
        )

    # Ensure the portfolio exists before uploading assets
    await retrieve_portfolio_by_user_id(user_id=token.userId)

    try:
        get_r2_settings()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudflare R2 environment variables not configured",
        )

    url_updates = {}
    for field, upload in uploads.items():
        if not upload:
            continue
        _ensure_image_upload(upload, field)
        file_bytes = await upload.read()
        if not file_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} upload is empty",
            )
        extension = _resolve_image_extension(upload)
        key = f"branding/{token.userId}/{field.lower()}_{uuid.uuid4().hex}{extension}"
        try:
            public_url = await anyio.to_thread.run_sync(
                upload_bytes,
                file_bytes,
                key,
                upload.content_type,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to upload {field}: {exc}",
            )
        url_updates[field] = public_url

    updates = {f"metadata.{field}": url for field, url in url_updates.items()}
    updates["last_updated"] = int(time.time())
    updated_item = await update_portfolio_fields_by_user_id(
        updates,
        user_id=token.userId,
        push_updates=None,
    )
    background_tasks.add_task(trigger_portfolio_revalidate)

    return APIResponse(
        status_code=200,
        data=url_updates,
        detail="Metadata images updated",
    )


@router.post(
    "/analyze",
    response_model=APIResponse[AnalyzePortfolioResponse],
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
)
async def analyze_portfolio_document(
    file: UploadFile = File(...),
    token: accessTokenOut = Depends(verify_token),
):
    try:
        extracted_text, file_url = await process_portfolio_document(file, token.userId)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    try:
        current_portfolio = await retrieve_portfolio_by_user_id(user_id=token.userId)
        current_portfolio_dict = current_portfolio.model_dump()
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
        current_portfolio_dict = build_empty_portfolio_schema(token.userId)
    try:
        suggestions = generate_portfolio_suggestions(
            extracted_text,
            current_portfolio_dict,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI suggestion generation failed: {exc}",
        )

    return APIResponse(
        status_code=200,
        data=AnalyzePortfolioResponse(fileUrl=file_url, suggestions=suggestions),
        detail="Portfolio analysis complete",
    )


@router.post(
    "/apply",
    response_model=APIResponse[PortfolioOut],
    dependencies=[Depends(verify_token), Depends(check_user_account_status_and_permissions)],
)
async def apply_portfolio_suggestions(
    payload: ApplySuggestionsRequest,
    background_tasks: BackgroundTasks,
    token: accessTokenOut = Depends(verify_token),
):
    payload.updates = _expand_contact_legacy_updates(payload.updates)
    payload.updates = _prune_root_updates_with_children(payload.updates)
    for item in payload.updates:
        item.value = _maybe_parse_json(item.value)
        item.field = _map_field_aliases(item.field)
    payload.updates = _coalesce_indexed_children(payload.updates)
    payload.updates = _prune_parent_index_updates(payload.updates)
    _validate_update_fields([item.field for item in payload.updates])

    try:
        current_data = await retrieve_portfolio_raw_by_user_id(user_id=token.userId)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
        created = await add_portfolio(build_empty_portfolio_create(token.userId), token.userId)
        current_data = created.model_dump()

    for item in payload.updates:
        item.expectedCurrent = _maybe_parse_json(item.expectedCurrent)

    updates = {}
    for item in payload.updates:
        field = item.field
        if isinstance(item.value, str) and field.endswith(".current"):
            lowered = item.value.strip().lower()
            if lowered in ("true", "false"):
                item.value = lowered == "true"
        item.value = _coerce_list_field(field, item.value)
        item.value = _coerce_leaf_list_field(field, item.value)
        normalized_value = normalize_update(field, item.value)
        normalized_value = _normalize_indexed_update(field, normalized_value)
        if _apply_indexed_list_set(updates, current_data, field, normalized_value):
            continue
        updates[_field_path_to_mongo(field)] = normalized_value

    updates["last_updated"] = int(time.time())

    updated_item = await update_portfolio_fields_by_user_id(
        updates,
        user_id=token.userId,
        push_updates=None,
    )
    background_tasks.add_task(trigger_portfolio_revalidate)

    return APIResponse(
        status_code=200,
        data=updated_item,
        detail="Portfolio updated from suggestions",
    )
