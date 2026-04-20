from src.chunking.text import TextChunk
from src.services.semantic_review import select_chunks_for_semantic_review


def test_select_chunks_for_semantic_review_marks_suspicious_and_sampled() -> None:
    chunks = [
        TextChunk(page_number=1, text="Corto"),
        TextChunk(page_number=1, text="Contenido normal con cierre adecuado."),
        TextChunk(page_number=2, text="Texto con corte sospechoso:"),
        TextChunk(page_number=3, text="X" * 2500),
    ]

    selections = select_chunks_for_semantic_review(
        chunks,
        min_chars=20,
        max_chars=2200,
        sample_rate=1.0,
        sample_seed="manual:1",
    )

    reasons = {(selection.chunk_index, selection.reason) for selection in selections}
    assert (0, "too_short") in reasons
    assert (2, "suspicious_boundary") in reasons
    assert (3, "too_long") in reasons
    assert (1, "sampled") in reasons
