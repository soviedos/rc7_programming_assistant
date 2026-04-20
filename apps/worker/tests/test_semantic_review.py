from src.chunking.text import TextChunk
from src.services.semantic_review import (
    ChunkReviewResult,
    build_review_metrics_summary,
    is_manual_eligible_for_semantic_review,
    select_chunks_for_semantic_review,
)


class ManualStub:
    def __init__(self, title: str, document_language: str) -> None:
        self.title = title
        self.document_language = document_language


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


def test_is_manual_eligible_for_semantic_review_uses_language_and_title(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "src.services.semantic_review.settings.semantic_review_enabled_languages",
        "es,en",
    )
    monkeypatch.setattr(
        "src.services.semantic_review.settings.semantic_review_title_include_terms",
        "programmer,operacion",
    )

    assert is_manual_eligible_for_semantic_review(
        ManualStub("RC7 Programmer Manual", "en")
    )
    assert not is_manual_eligible_for_semantic_review(ManualStub("Guia general", "en"))
    assert not is_manual_eligible_for_semantic_review(ManualStub("Programmer", "fr"))


def test_build_review_metrics_summary_aggregates_scores_actions_and_cost(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "src.services.semantic_review.settings.semantic_review_estimated_output_tokens",
        100,
    )
    monkeypatch.setattr(
        "src.services.semantic_review.settings.semantic_review_cost_input_per_1k_tokens",
        0.001,
    )
    monkeypatch.setattr(
        "src.services.semantic_review.settings.semantic_review_cost_output_per_1k_tokens",
        0.002,
    )
    monkeypatch.setattr(
        "src.services.semantic_review.settings.semantic_review_min_chars",
        200,
    )

    results = [
        ChunkReviewResult(
            chunk_index=0,
            page_number=1,
            review_status="reviewed",
            action="keep",
            coherence_score=0.9,
            completeness_score=0.8,
            boundary_quality_score=0.7,
            raw_response='{"ok":true}',
        ),
        ChunkReviewResult(
            chunk_index=1,
            page_number=1,
            review_status="reviewed",
            action="split",
            coherence_score=0.5,
            completeness_score=0.6,
            boundary_quality_score=0.4,
            raw_response='{"ok":true}',
        ),
        ChunkReviewResult(
            chunk_index=2,
            page_number=2,
            review_status="error",
            action="merge_with_next",
            reason="timeout",
        ),
    ]

    summary = build_review_metrics_summary(
        manual_id=12,
        initial_chunk_count=4,
        final_chunk_count=3,
        review_results=results,
        applied_autofixes=1,
    )

    assert summary.manual_id == 12
    assert summary.initial_chunk_count == 4
    assert summary.final_chunk_count == 3
    assert summary.reviewed_count == 2
    assert summary.error_count == 1
    assert summary.keep_actions == 1
    assert summary.split_actions == 1
    assert summary.merge_actions == 1
    assert summary.applied_autofixes == 1
    assert summary.avg_coherence_score == 0.7
    assert summary.avg_completeness_score == 0.7
    assert summary.avg_boundary_quality_score == 0.55
    assert summary.estimated_input_tokens > 0
    assert summary.estimated_output_tokens == 300
    assert summary.estimated_cost_usd > 0
