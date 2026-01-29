
from fastapi import APIRouter, HTTPException, Query, Path, status, Depends, BackgroundTasks, UploadFile, File
from typing import List, Optional
import json
import time
import uuid
import anyio
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
)
from security.auth import verify_token
from security.account_status_check import check_user_account_status_and_permissions
from services.r2_service import get_r2_settings, build_public_url, upload_pdf_bytes
from services.portfolio_service import (
    add_portfolio,
    remove_portfolio_by_user_id,
    retrieve_portfolios,
    retrieve_portfolio_by_user_id,
    retrieve_portfolio_raw_by_user_id,
    update_portfolio_by_user_id,
    update_portfolio_fields_by_user_id,
)
from services.revalidate_service import trigger_portfolio_revalidate
from services.document_service import process_portfolio_document
from services.ai_portfolio_suggestions import generate_portfolio_suggestions
from services.portfolio_normalization import normalize_update

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


ALLOWED_PORTFOLIO_PREFIXES = {
    "navItems",
    "footer",
    "hero",
    "experience",
    "projects",
    "skillGroups",
    "contacts",
    "theme",
    "animations",
    "metadata",
    "resumeUrl",
}


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




async def _upload_resume_and_update(user_id: str, file_bytes: bytes, key: str, resume_url: str):
    await anyio.to_thread.run_sync(upload_pdf_bytes, file_bytes, key)
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

    current_portfolio = await retrieve_portfolio_by_user_id(user_id=token.userId)
    try:
        suggestions = generate_portfolio_suggestions(
            extracted_text,
            current_portfolio.model_dump(),
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
    _validate_update_fields([item.field for item in payload.updates])

    current_data = await retrieve_portfolio_raw_by_user_id(user_id=token.userId)

    conflicts = []
    for item in payload.updates:
        item.expectedCurrent = _maybe_parse_json(item.expectedCurrent)
        if item.expectedCurrent is None:
            continue
        current_value = _read_value_at_path(current_data, item.field)
        tokens = _path_to_tokens(item.field)
        if tokens and isinstance(tokens[-1], int):
            continue
        if current_value is None and tokens and isinstance(tokens[-1], int):
            parent_tokens = tokens[:-1]
            parent_value = _read_value_at_path(current_data, _tokens_to_mongo(parent_tokens))
            index = tokens[-1]
            if isinstance(parent_value, list) and index == len(parent_value) and item.expectedCurrent in ("", [], {}):
                continue
        if current_value != item.expectedCurrent:
            conflicts.append({"field": item.field, "currentValue": current_value})

    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflicts detected: {conflicts}",
        )

    updates = {}
    push_updates = {}
    for item in payload.updates:
        item.value = _maybe_parse_json(item.value)
        normalized_value = normalize_update(item.field, item.value)
        tokens = _path_to_tokens(item.field)
        if tokens and isinstance(tokens[-1], int):
            parent_tokens = tokens[:-1]
            parent_value = _read_value_at_path(current_data, _tokens_to_mongo(parent_tokens))
            index = tokens[-1]
            if isinstance(parent_value, list) and index == len(parent_value):
                _append_push_updates(push_updates, _tokens_to_mongo(parent_tokens), normalized_value)
                continue
        updates[_field_path_to_mongo(item.field)] = normalized_value

    updates["last_updated"] = int(time.time())

    updated_item = await update_portfolio_fields_by_user_id(
        updates,
        user_id=token.userId,
        push_updates=push_updates,
    )
    background_tasks.add_task(trigger_portfolio_revalidate)

    return APIResponse(
        status_code=200,
        data=updated_item,
        detail="Portfolio updated from suggestions",
    )
