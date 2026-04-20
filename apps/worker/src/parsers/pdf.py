from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text_by_page(content: bytes) -> list[str]:
    reader = PdfReader(BytesIO(content))
    return [(page.extract_text() or "").strip() for page in reader.pages]
