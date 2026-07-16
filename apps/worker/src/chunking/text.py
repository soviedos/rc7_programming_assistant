from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    page_number: int
    text: str
    # Sección del manual a la que pertenece, tomada del outline del PDF. None si
    # el PDF no trae outline. No influye en dónde se corta: solo anota.
    section_title: str | None = None


def build_text_chunks(
    page_texts: list[str],
    max_chars: int = 1200,
    page_sections: dict[int, str] | None = None,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    sections = page_sections or {}

    for page_number, page_text in enumerate(page_texts, start=1):
        normalized_text = page_text.strip()
        if not normalized_text:
            continue

        section = sections.get(page_number)

        # normalized_text is non-empty here, so this always yields at least one.
        paragraphs = [paragraph.strip() for paragraph in normalized_text.split("\n\n") if paragraph.strip()]

        current_parts: list[str] = []
        current_length = 0

        for paragraph in paragraphs:
            paragraph_length = len(paragraph)

            if paragraph_length > max_chars:
                if current_parts:
                    chunks.append(TextChunk(page_number=page_number, text="\n\n".join(current_parts), section_title=section))
                    current_parts = []
                    current_length = 0

                chunks.extend(_split_long_text(page_number, paragraph, max_chars, section))
                continue

            projected_length = current_length + paragraph_length + (2 if current_parts else 0)
            if projected_length > max_chars and current_parts:
                chunks.append(TextChunk(page_number=page_number, text="\n\n".join(current_parts), section_title=section))
                current_parts = [paragraph]
                current_length = paragraph_length
            else:
                current_parts.append(paragraph)
                current_length = projected_length

        if current_parts:
            chunks.append(TextChunk(page_number=page_number, text="\n\n".join(current_parts), section_title=section))

    return chunks


def _split_long_text(
    page_number: int, text: str, max_chars: int, section: str | None = None
) -> list[TextChunk]:
    return [
        TextChunk(
            page_number=page_number,
            text=text[index : index + max_chars].strip(),
            section_title=section,
        )
        for index in range(0, len(text), max_chars)
        if text[index : index + max_chars].strip()
    ]
