from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from schemas.response_schema import APIResponse
from schemas.tokens_schema import accessTokenOut
from security.auth import verify_token
from security.account_status_check import check_user_account_status_and_permissions
from services.document_processor import DocumentProcessor
from services.ai_patch_service import AIPatchService
from services.portfolio_service import retrieve_portfolio_by_user_id

router = APIRouter(prefix="/suggestions", tags=["AI Suggestions"])


@router.post(
    "/generate",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(check_user_account_status_and_permissions)],
)
async def generate_suggestion(
    target_path: str = Form(..., description="Section or field path, e.g., hero.title or experience[0].role"),
    text_input: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    use_existing_resume: bool = Form(False),
    token: accessTokenOut = Depends(verify_token),
):
    """
    Generate a minimal patch payload for the requested portfolio field/section.
    Input sources: inline text, uploaded file, or an already uploaded resume.
    """
    resume_url: Optional[str] = None
    if use_existing_resume:
        try:
            portfolio = await retrieve_portfolio_by_user_id(user_id=token.userId)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(status_code=400, detail="No portfolio found for this user") from exc
            raise
        resume_url = getattr(portfolio, "resumeUrl", None)
        if not resume_url:
            raise HTTPException(status_code=400, detail="No resume stored for this user to reuse")

    processor = DocumentProcessor()
    try:
        clean_text = await processor.get_content(text_input, file, resume_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ai_service = AIPatchService()
    try:
        patch_payload = await ai_service.generate_patch(target_path, clean_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}") from exc

    return APIResponse(
        status_code=200,
        data={
            "target": target_path,
            "patch": patch_payload,
            "source_length": len(clean_text),
        },
        detail="Suggestion generated",
    )
