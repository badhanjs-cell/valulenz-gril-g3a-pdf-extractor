from __future__ import annotations

import hashlib
import os
from typing import Any
from urllib.parse import quote

import fitz  # PyMuPDF
import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


APP_VERSION = "VALULENZ-G3A-PDF-EXTRACTOR-v1.0.0"

SUPABASE_PROJECT_URL = os.getenv("SUPABASE_PROJECT_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
PDF_EXTRACTOR_API_KEY = os.getenv("PDF_EXTRACTOR_API_KEY", "")
MAX_PDF_BYTES = int(os.getenv("MAX_PDF_BYTES", "104857600"))
DOWNLOAD_TIMEOUT_SECONDS = float(os.getenv("DOWNLOAD_TIMEOUT_SECONDS", "120"))

app = FastAPI(
    title="Valulenz GRIL G3A PDF Extractor",
    version=APP_VERSION,
)


class ExtractPdfRequest(BaseModel):
    snapshot_id: int = Field(gt=0)
    storage_bucket: str = Field(min_length=1, max_length=200)
    storage_object_path: str = Field(min_length=1, max_length=2000)
    expected_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    expected_byte_size: int = Field(gt=0)
    language_hint: str | None = Field(default=None, max_length=20)
    resolved_url: str | None = Field(default=None, max_length=4000)
    minimum_characters: int = Field(default=1000, ge=100, le=1000000)


def _assert_runtime_configuration() -> None:
    missing = []
    if not SUPABASE_PROJECT_URL:
        missing.append("SUPABASE_PROJECT_URL")
    if not SUPABASE_SECRET_KEY:
        missing.append("SUPABASE_SECRET_KEY")
    if not PDF_EXTRACTOR_API_KEY:
        missing.append("PDF_EXTRACTOR_API_KEY")
    if missing:
        raise RuntimeError("Missing Railway environment variables: " + ", ".join(missing))


def _failure(code: str, message: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "success": False,
        "response_status": "PDF_EXTRACTION_FAILED",
        "error_code": code,
        "error_message": message[:4000],
        "extractor_version": APP_VERSION,
    }
    payload.update(extra)
    return payload


@app.get("/health")
async def health() -> dict[str, Any]:
    configured = bool(
        SUPABASE_PROJECT_URL and SUPABASE_SECRET_KEY and PDF_EXTRACTOR_API_KEY
    )
    return {
        "success": True,
        "status": "healthy" if configured else "configuration_required",
        "version": APP_VERSION,
        "configured": configured,
        "engine": "PyMuPDF",
        "ocr_enabled": False,
    }


@app.post("/extract-regulatory-pdf")
async def extract_regulatory_pdf(
    request: ExtractPdfRequest,
    x_extractor_key: str | None = Header(default=None, alias="X-Extractor-Key"),
) -> dict[str, Any]:
    try:
        _assert_runtime_configuration()
    except RuntimeError as exc:
        return _failure("EXTRACTOR_NOT_CONFIGURED", str(exc))

    if not x_extractor_key or x_extractor_key != PDF_EXTRACTOR_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid extractor API key.")

    if request.expected_byte_size > MAX_PDF_BYTES:
        return _failure(
            "PDF_TOO_LARGE",
            f"Expected PDF size {request.expected_byte_size} exceeds configured limit "
            f"{MAX_PDF_BYTES}.",
        )

    bucket = quote(request.storage_bucket, safe="")
    object_path = quote(request.storage_object_path, safe="/")
    storage_url = (
        f"{SUPABASE_PROJECT_URL}/storage/v1/object/authenticated/"
        f"{bucket}/{object_path}"
    )

    try:
        timeout = httpx.Timeout(DOWNLOAD_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(
                storage_url,
                headers={
                    "apikey": SUPABASE_SECRET_KEY,
                    "Cache-Control": "no-store",
                    "Accept": "application/pdf,application/octet-stream,*/*;q=0.1",
                },
            )
    except Exception as exc:
        return _failure(
            "STORAGE_DOWNLOAD_FAILED",
            f"Private Storage download failed: {type(exc).__name__}: {exc}",
        )

    if response.status_code != 200:
        return _failure(
            "STORAGE_HTTP_ERROR",
            f"Private Storage returned HTTP {response.status_code}.",
            storage_http_status=response.status_code,
        )

    pdf_bytes = response.content
    actual_size = len(pdf_bytes)
    actual_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

    if actual_size != request.expected_byte_size:
        return _failure(
            "SOURCE_BYTE_SIZE_MISMATCH",
            f"Expected {request.expected_byte_size} bytes but downloaded {actual_size}.",
            source_byte_size=actual_size,
            source_sha256=actual_sha256,
        )

    if actual_sha256.lower() != request.expected_sha256.lower():
        return _failure(
            "SOURCE_SHA256_MISMATCH",
            "Downloaded immutable object SHA-256 does not match the G2 snapshot.",
            source_byte_size=actual_size,
            source_sha256=actual_sha256,
        )

    if not pdf_bytes.startswith(b"%PDF-"):
        return _failure(
            "INVALID_PDF_MAGIC",
            "The immutable object does not begin with the required %PDF- signature.",
            source_byte_size=actual_size,
            source_sha256=actual_sha256,
        )

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        return _failure(
            "PDF_OPEN_FAILED",
            f"PyMuPDF could not open the verified PDF: {type(exc).__name__}: {exc}",
            source_byte_size=actual_size,
            source_sha256=actual_sha256,
        )

    page_count = document.page_count
    page_blocks: list[str] = []
    pages_with_text = 0

    try:
        for page_number in range(page_count):
            page = document.load_page(page_number)
            page_text = page.get_text("text", sort=True).replace("\x00", "")
            page_text = page_text.rstrip()

            if page_text.strip():
                pages_with_text += 1

            page_blocks.append(
                f"===== PAGE {page_number + 1} OF {page_count} =====\n{page_text}"
            )
    except Exception as exc:
        document.close()
        return _failure(
            "PDF_TEXT_EXTRACTION_FAILED",
            f"PyMuPDF text extraction failed: {type(exc).__name__}: {exc}",
            source_byte_size=actual_size,
            source_sha256=actual_sha256,
            page_count=page_count,
        )
    finally:
        if not document.is_closed:
            document.close()

    extracted_text = "\n\n".join(page_blocks).strip()
    character_count = len(extracted_text)

    if character_count < request.minimum_characters:
        return _failure(
            "PDF_TEXT_LAYER_INSUFFICIENT",
            f"Only {character_count} characters were extracted; "
            f"minimum required is {request.minimum_characters}. OCR is not enabled "
            "in this controlled v1 worker.",
            source_byte_size=actual_size,
            source_sha256=actual_sha256,
            page_count=page_count,
            pages_with_text=pages_with_text,
            character_count=character_count,
        )

    extracted_text_sha256 = hashlib.sha256(
        extracted_text.encode("utf-8")
    ).hexdigest()

    coverage = pages_with_text / page_count if page_count else 0.0
    average_characters = character_count / page_count if page_count else 0.0

    if coverage >= 0.98 and average_characters >= 250:
        confidence = 0.99
    elif coverage >= 0.90 and average_characters >= 100:
        confidence = 0.96
    elif coverage >= 0.75:
        confidence = 0.90
    else:
        confidence = 0.80

    language_code = (request.language_hint or "und").strip().lower() or "und"

    return {
        "success": True,
        "response_status": "PDF_TEXT_EXTRACTED_AND_SOURCE_VERIFIED",
        "extraction_method": "PDF_TEXT",
        "extraction_engine": "PYMUPDF",
        "extraction_engine_version": fitz.VersionBind,
        "extractor_version": APP_VERSION,
        "extracted_text": extracted_text,
        "extracted_text_sha256": extracted_text_sha256,
        "character_count": character_count,
        "page_count": page_count,
        "pages_with_text": pages_with_text,
        "language_code": language_code,
        "extraction_confidence": confidence,
        "source_sha256": actual_sha256,
        "source_byte_size": actual_size,
        "text_layer_found": pages_with_text > 0,
        "ocr_used": False,
        "storage_response_content_type": response.headers.get("content-type"),
        "resolved_url": request.resolved_url,
        "snapshot_id": request.snapshot_id,
    }
