import io
from typing import Optional

from fastapi import UploadFile
from docx import Document
from pypdf import PdfReader

from services.storage import download_file_as_bytes


class DocumentProcessor:
    """
    Extracts plain text from raw strings, uploaded files, or existing resume URLs.
    """

    _MAX_CHARS = 15_000

    async def get_content(
        self,
        text_input: Optional[str],
        file: Optional[UploadFile],
        resume_url: Optional[str],
    ) -> str:
        """
        Priority order:
        1) Explicit text_input
        2) Newly uploaded file
        3) Existing resume_url
        """
        if text_input and text_input.strip():
            return self._truncate(text_input.strip())

        file_bytes: bytes | None = None
        filename = ""

        if file is not None:
            filename = file.filename or "upload"
            file_bytes = await file.read()
        elif resume_url:
            filename = resume_url
            file_bytes = download_file_as_bytes(resume_url)

        if not file_bytes:
            raise ValueError("No valid input source provided (text, file, or resume)")

        extracted = self._extract_text(file_bytes, filename)
        return self._truncate(extracted)

    def _extract_text(self, data: bytes, filename: str) -> str:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext == "pdf":
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(filter(None, [page.extract_text() for page in reader.pages]))
        if ext in {"docx", "doc"}:
            doc = Document(io.BytesIO(data))
            return "\n".join([p.text for p in doc.paragraphs if p.text])
        if ext in {"txt", ""}:
            return data.decode("utf-8", errors="ignore")
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}")

    def _truncate(self, text: str) -> str:
        if len(text) <= self._MAX_CHARS:
            return text
        return text[: self._MAX_CHARS]
