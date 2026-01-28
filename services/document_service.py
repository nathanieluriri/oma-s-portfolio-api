import io
import os
import tempfile
import uuid
from typing import Tuple

from fastapi import UploadFile

from services.malware_scan import scan_bytes_for_malware
from services.r2_service import build_public_url, get_r2_settings
import boto3


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}


def _max_document_bytes() -> int:
    return int(os.getenv("MAX_DOCUMENT_BYTES", str(10 * 1024 * 1024)))


def _get_extension(filename: str) -> str:
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return "bin"


def _is_text_mime(mime: str) -> bool:
    return mime.startswith("text/")


def _validate_file(file: UploadFile) -> None:
    if not file.filename:
        raise ValueError("Missing filename")
    if not file.content_type:
        raise ValueError("Missing content type")
    if file.content_type not in ALLOWED_MIME_TYPES and not _is_text_mime(file.content_type):
        raise ValueError(f"Unsupported content type: {file.content_type}")


def _upload_to_r2(file_bytes: bytes, filename: str, content_type: str, user_id: str) -> str:
    endpoint_url, access_key, secret_key, bucket = get_r2_settings()
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )
    key = f"uploads/portfolio/{user_id}/{uuid.uuid4().hex}-{filename}"
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type,
    )
    return build_public_url(endpoint_url, bucket, key)


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _extract_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text]
    return "\n".join(paragraphs).strip()


def _extract_text(file_bytes: bytes, content_type: str, filename: str) -> str:
    extension = _get_extension(filename)
    if content_type == "application/pdf" or extension == "pdf":
        return _extract_text_from_pdf(file_bytes)
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or extension == "docx":
        return _extract_text_from_docx(file_bytes)
    return file_bytes.decode("utf-8", errors="ignore").strip()


async def process_portfolio_document(
    file: UploadFile,
    user_id: str,
) -> Tuple[str, str]:
    _validate_file(file)

    file_bytes = await file.read()
    if len(file_bytes) > _max_document_bytes():
        raise ValueError("File too large")

    file_url = _upload_to_r2(file_bytes, file.filename, file.content_type, user_id)

    is_safe = scan_bytes_for_malware(file_bytes)
    if not is_safe:
        raise ValueError("Malware detected in uploaded file")

    extracted_text = _extract_text(file_bytes, file.content_type, file.filename)
    if not extracted_text:
        raise ValueError("No extractable text found in document")

    return extracted_text, file_url
