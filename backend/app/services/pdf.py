"""PDF validation and page-accurate text extraction."""

from dataclasses import dataclass, field

import fitz

from app.ai.types import PageText
from app.core.config import Settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger("insurio.pdf")

PDF_MAGIC = b"%PDF-"
MIN_OCR_TEXT_CHARS = 40


@dataclass
class ExtractionResult:
    pages: list[PageText] = field(default_factory=list)
    page_count: int = 0
    ocr_pages: int = 0
    encrypted: bool = False

    @property
    def total_chars(self) -> int:
        return sum(len(page.text) for page in self.pages)


def validate_pdf_bytes(data: bytes, settings: Settings) -> None:
    if not data:
        raise AppError("The uploaded file is empty.", code="empty_file", status_code=400)
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > limit:
        raise AppError(
            f"The file exceeds the {settings.MAX_UPLOAD_MB} MB limit.",
            code="file_too_large",
            status_code=413,
        )
    if not data.startswith(PDF_MAGIC):
        # Content sniffing, not just the extension: rejects renamed files.
        raise AppError("The file is not a valid PDF.", code="invalid_pdf_type", status_code=415)


def _ocr_page(page: "fitz.Page") -> str:
    try:
        import io

        import pytesseract
        from PIL import Image

        pixmap = page.get_pixmap(dpi=200)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        return str(pytesseract.image_to_string(image))
    except Exception:
        logger.warning("ocr_failed", extra={"event": "ocr_failed"})
        return ""


def extract_pdf(data: bytes, settings: Settings) -> ExtractionResult:
    validate_pdf_bytes(data, settings)
    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise AppError(
            "The PDF could not be opened. It may be corrupt.",
            code="pdf_unreadable",
            status_code=400,
        ) from exc

    try:
        if document.needs_pass:
            return ExtractionResult(page_count=len(document), encrypted=True)
        if len(document) > settings.MAX_PDF_PAGES:
            raise AppError(
                f"The PDF has more than {settings.MAX_PDF_PAGES} pages.",
                code="pdf_too_many_pages",
                status_code=413,
            )

        pages: list[PageText] = []
        ocr_pages = 0
        for index, page in enumerate(document, start=1):
            text = page.get_text("text") or ""
            method = "text"
            if len(text.strip()) < MIN_OCR_TEXT_CHARS and settings.OCR_ENABLED:
                ocr_text = _ocr_page(page)
                if len(ocr_text.strip()) > len(text.strip()):
                    text = ocr_text
                    method = "ocr"
                    ocr_pages += 1
            if not text.strip():
                method = "empty"
            pages.append(PageText(page_number=index, text=text, extraction_method=method))

        return ExtractionResult(
            pages=pages,
            page_count=len(document),
            ocr_pages=ocr_pages,
            encrypted=False,
        )
    finally:
        document.close()
