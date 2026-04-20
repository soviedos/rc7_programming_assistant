from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    page_number: int
    text: str


def build_text_chunks(page_texts: list[str], max_chars: int = 1200) -> list[TextChunk]:
    chunks: list[TextChunk] = []

    for page_number, page_text in enumerate(page_texts, start=1):
        normalized_text = page_text.strip()
        if not normalized_text:
            continue

        paragraphs = [paragraph.strip() for paragraph in normalized_text.split("\n\n") if paragraph.strip()]
        if not paragraphs:
            paragraphs = [normalized_text]

        current_parts: list[str] = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph)

            if paragraph_length > max_chars:
                if current_parts:
                    chunks.append(TextChunk(page_number=page_number, text="\n\n".join(current_parts)))
                    current_parts = []
                    current_length = 0

                chunks.extend(_split_long_text(page_number, paragraph, max_chars))
                continue

            projected_length = current_length + paragraph_length + (2 if current_parts else 0)
            if projected_length > max_chars and current_parts:
                chunks.append(TextChunk(page_number=page_number, text="\n\n".join(current_parts)))
                current_parts = [paragraph]
                current_length = paragraph_length
            else:
                current_parts.append(paragraph)
                current_length = projected_length

        if current_parts:
            chunks.append(TextChunk(page_number=page_number, text="\n\n".join(current_parts)))

    return chunks


def _split_long_text(page_number: int, text: str, max_chars: int) -> list[TextChunk]:
    return [
        TextChunk(page_number=page_number, text=text[index : index + max_chars].strip())
        for index in range(0, len(text), max_chars)
        if text[index : index + max_chars].strip()
    ]
