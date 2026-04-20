from src.chunking.text import build_text_chunks


def test_build_text_chunks_splits_paragraphs_and_long_sections() -> None:
    chunks = build_text_chunks(
        [
            "MOVE P, HOME\n\nWAIT SIG(1)",
            "A" * 1500,
        ],
        max_chars=1000,
    )

    assert len(chunks) == 3
    assert chunks[0].page_number == 1
    assert chunks[0].text == "MOVE P, HOME\n\nWAIT SIG(1)"
    assert chunks[1].page_number == 2
    assert len(chunks[1].text) == 1000
    assert chunks[2].page_number == 2
    assert len(chunks[2].text) == 500
