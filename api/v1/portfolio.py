
from fastapi import APIRouter, HTTPException, Query, Path, status, Depends, BackgroundTasks, UploadFile, File
from typing import List, Optional
import json
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
from security.auth import verify_token
from security.account_status_check import check_user_account_status_and_permissions
from services.r2_service import get_r2_settings, build_public_url, upload_pdf_bytes
from services.portfolio_service import (
    add_portfolio,
    remove_portfolio_by_user_id,
    retrieve_portfolios,
    retrieve_portfolio_by_user_id,
    update_portfolio_by_user_id,
)

router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


async def _upload_resume_and_update(user_id: str, file_bytes: bytes, key: str, resume_url: str):
    await anyio.to_thread.run_sync(upload_pdf_bytes, file_bytes, key)
    await update_portfolio_by_user_id(portfolio_data=PortfolioUpdate(resumeUrl=resume_url), user_id=user_id)

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
    token: accessTokenOut = Depends(verify_token),
):
    """
    Updates an existing Portfolio by its ID.
    Assumes the service layer handles partial updates (e.g., ignores None fields in payload).
    """
    updated_item = await update_portfolio_by_user_id(portfolio_data=payload, user_id=token.userId)
    if not updated_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Portfolio not found or update failed")
    
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
