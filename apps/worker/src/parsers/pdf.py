from __future__ import annotations

from io import BytesIO

import pytesseract
from pdf2image import convert_from_bytes
from pypdf import PdfReader


def extract_pdf_text_by_page(content: bytes) -> list[str]:
    reader = PdfReader(BytesIO(content))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    total_pages = len(pages)

    non_empty = sum(1 for p in pages if p)
    if not pages or non_empty < max(1, total_pages * 0.2):
        return _extract_with_ocr(content, total_pages)

    return pages


def _extract_with_ocr(content: bytes, total_pages: int) -> list[str]:
    results: list[str] = []
    for page_num in range(1, total_pages + 1):
        images = convert_from_bytes(
            content,
            dpi=150,
            first_page=page_num,
            last_page=page_num,
        )
        text = (
            pytesseract.image_to_string(images[0], lang="spa+eng").strip()
            if images
            else ""
        )
        results.append(text)
    return results
