"""Tests for pgvector-backed chunk retrieval in the chat service.

Exercises the real ``<=>`` cosine ordering in PostgreSQL plus the in-Python
re-ranking (hardware-compatibility + category) applied on the vector pool.
"""

from __future__ import annotations

import math

import pytest
from sqlalchemy.orm import Session

from src.api.v1.schemas.chat import ChatRequest
from src.db.models import EMBEDDING_DIM, Manual, ManualChunk
from src.services.chat.service import _retrieve_chunks


def _unit_axis(index: int) -> list[float]:
    """A 3072-dim unit vector with a single 1.0 at ``index``."""
    vec = [0.0] * EMBEDDING_DIM
    vec[index] = 1.0
    return vec


def _sim_vector(similarity: float) -> list[float]:
    """Unit vector whose cosine similarity with ``_unit_axis(0)`` is ``similarity``."""
    vec = [0.0] * EMBEDDING_DIM
    vec[0] = similarity
    vec[1] = math.sqrt(max(0.0, 1.0 - similarity * similarity))
    return vec


def _payload(*, robot_type: str = "VP-6242", controller: str = "RC7") -> ChatRequest:
    return ChatRequest(prompt="q", robot_type=robot_type, controller=controller)


def _make_manual(
    db: Session,
    *,
    title: str,
    storage_key: str,
    categories: list[str],
    robot_model: str | None = None,
    controller_version: str | None = None,
    status: str = "indexed",
) -> Manual:
    manual = Manual(
        title=title,
        original_filename="m.pdf",
        storage_key=storage_key,
        content_type="application/pdf",
        size_bytes=100,
        status=status,
        categories=categories,
        robot_model=robot_model,
        controller_version=controller_version,
        uploaded_by_user_id=1,
        uploaded_by_email="admin@test.com",
    )
    db.add(manual)
    db.commit()
    db.refresh(manual)
    return manual


def test_retrieve_chunks_orders_by_cosine_distance(db_session: Session) -> None:
    """Closest chunk by cosine distance ranks first (no category boost)."""
    manual = _make_manual(
        db_session, title="Plain", storage_key="k/plain.pdf", categories=[]
    )
    # Three orthogonal embeddings; query matches the first axis exactly.
    db_session.add_all(
        [
            ManualChunk(
                manual_id=manual.id,
                chunk_index=i,
                page_number=i + 1,
                text=f"chunk-{i}",
                embedding=_unit_axis(i),
            )
            for i in range(3)
        ]
    )
    db_session.commit()

    results = _retrieve_chunks(db_session, _unit_axis(0), _payload(), top_k=3)

    assert [chunk.text for chunk, _m, _s in results] == ["chunk-0", "chunk-1", "chunk-2"]
    # Exact match → similarity ~1.0; orthogonal → ~0.0.
    assert results[0][2] > 0.99
    assert results[1][2] < 0.01


def test_retrieve_chunks_applies_category_boost(db_session: Session) -> None:
    """A boosted category can outrank a raw-closer chunk after re-ranking."""
    plain = _make_manual(
        db_session, title="Plain", storage_key="k/plain2.pdf", categories=[]
    )
    boosted = _make_manual(
        db_session,
        title="Programming",
        storage_key="k/prog.pdf",
        categories=["programming"],  # boost 1.30
    )

    # Raw similarity: plain (0.80) is closer than boosted (0.70).
    db_session.add(
        ManualChunk(
            manual_id=plain.id,
            chunk_index=0,
            page_number=1,
            text="plain-chunk",
            embedding=_sim_vector(0.80),
        )
    )
    db_session.add(
        ManualChunk(
            manual_id=boosted.id,
            chunk_index=0,
            page_number=1,
            text="boosted-chunk",
            embedding=_sim_vector(0.70),
        )
    )
    db_session.commit()

    results = _retrieve_chunks(db_session, _unit_axis(0), _payload(), top_k=2)

    # After boost: 0.70 * 1.30 = 0.91 > 0.80 → boosted chunk wins.
    assert results[0][0].text == "boosted-chunk"
    assert results[1][0].text == "plain-chunk"
    assert results[0][2] > results[1][2]


def test_retrieve_chunks_skips_chunks_without_embedding(db_session: Session) -> None:
    """Chunks with NULL embeddings are excluded from the vector search."""
    manual = _make_manual(
        db_session, title="Mixed", storage_key="k/mixed.pdf", categories=[]
    )
    db_session.add(
        ManualChunk(
            manual_id=manual.id,
            chunk_index=0,
            page_number=1,
            text="has-embedding",
            embedding=_unit_axis(0),
        )
    )
    db_session.add(
        ManualChunk(
            manual_id=manual.id,
            chunk_index=1,
            page_number=2,
            text="no-embedding",
            embedding=None,
        )
    )
    db_session.commit()

    results = _retrieve_chunks(db_session, _unit_axis(0), _payload(), top_k=5)

    assert [chunk.text for chunk, _m, _s in results] == ["has-embedding"]


def test_retrieve_chunks_excludes_non_indexed_manuals(db_session: Session) -> None:
    """Only chunks belonging to manuals with status='indexed' are searched."""
    indexed = _make_manual(
        db_session, title="Indexed", storage_key="k/idx.pdf", categories=[]
    )
    processing = _make_manual(
        db_session,
        title="Processing",
        storage_key="k/proc.pdf",
        categories=[],
        status="processing",
    )
    # Both chunks carry the exact query vector; only the indexed one is eligible.
    db_session.add(
        ManualChunk(
            manual_id=indexed.id,
            chunk_index=0,
            page_number=1,
            text="indexed-chunk",
            embedding=_unit_axis(0),
        )
    )
    db_session.add(
        ManualChunk(
            manual_id=processing.id,
            chunk_index=0,
            page_number=1,
            text="processing-chunk",
            embedding=_unit_axis(0),
        )
    )
    db_session.commit()

    results = _retrieve_chunks(db_session, _unit_axis(0), _payload(), top_k=5)

    assert [chunk.text for chunk, _m, _s in results] == ["indexed-chunk"]


# ── Hardware-compatibility re-ranking ──────────────────────────────


def test_matching_robot_outranks_raw_closer_other_robot(db_session: Session) -> None:
    """A manual matching the user's robot can outrank a raw-closer mismatch."""
    other = _make_manual(
        db_session,
        title="VS-060 manual",
        storage_key="k/vs060.pdf",
        categories=[],
        robot_model="VS-060",
        controller_version="RC7",
    )
    mine = _make_manual(
        db_session,
        title="VP-6242 manual",
        storage_key="k/vp6242.pdf",
        categories=[],
        robot_model="VP-6242",
        controller_version="RC7",
    )

    # Raw similarity favours the other-robot chunk (0.80 vs 0.70).
    db_session.add(
        ManualChunk(
            manual_id=other.id,
            chunk_index=0,
            page_number=1,
            text="other-robot",
            embedding=_sim_vector(0.80),
        )
    )
    db_session.add(
        ManualChunk(
            manual_id=mine.id,
            chunk_index=0,
            page_number=1,
            text="my-robot",
            embedding=_sim_vector(0.70),
        )
    )
    db_session.commit()

    results = _retrieve_chunks(
        db_session, _unit_axis(0), _payload(robot_type="VP-6242"), top_k=2
    )

    # mine: 0.70 * 1.30(match) = 0.91 ; other: 0.80 * 0.70(mismatch) = 0.56.
    assert results[0][0].text == "my-robot"
    assert results[1][0].text == "other-robot"


def test_missing_hardware_metadata_is_neutral(db_session: Session) -> None:
    """Chunks without robot/controller metadata keep pure similarity ordering."""
    manual = _make_manual(
        db_session,
        title="Generic",
        storage_key="k/generic.pdf",
        categories=[],
        robot_model=None,
        controller_version=None,
    )
    db_session.add_all(
        [
            ManualChunk(
                manual_id=manual.id,
                chunk_index=0,
                page_number=1,
                text="closer",
                embedding=_sim_vector(0.90),
            ),
            ManualChunk(
                manual_id=manual.id,
                chunk_index=1,
                page_number=2,
                text="farther",
                embedding=_sim_vector(0.50),
            ),
        ]
    )
    db_session.commit()

    results = _retrieve_chunks(
        db_session, _unit_axis(0), _payload(robot_type="VP-6242"), top_k=2
    )

    # No metadata → hardware_factor 1.0 → raw similarity order, no degradation.
    assert [chunk.text for chunk, _m, _s in results] == ["closer", "farther"]
    # Score equals raw similarity (no boost/penalty applied); halfvec precision.
    assert results[0][2] == pytest.approx(0.90, abs=0.02)


def test_controller_mismatch_penalised(db_session: Session) -> None:
    """A different controller family demotes an otherwise equally-close chunk."""
    same_ctrl = _make_manual(
        db_session,
        title="RC7 doc",
        storage_key="k/rc7.pdf",
        categories=[],
        controller_version="RC7.2",
    )
    other_ctrl = _make_manual(
        db_session,
        title="RC8 doc",
        storage_key="k/rc8.pdf",
        categories=[],
        controller_version="RC8.0",
    )
    db_session.add(
        ManualChunk(
            manual_id=same_ctrl.id,
            chunk_index=0,
            page_number=1,
            text="rc7-chunk",
            embedding=_sim_vector(0.75),
        )
    )
    db_session.add(
        ManualChunk(
            manual_id=other_ctrl.id,
            chunk_index=0,
            page_number=1,
            text="rc8-chunk",
            embedding=_sim_vector(0.75),
        )
    )
    db_session.commit()

    results = _retrieve_chunks(
        db_session, _unit_axis(0), _payload(controller="RC7"), top_k=2
    )

    # Equal similarity, but RC7 matches (×1.15) and RC8 is penalised (×0.85).
    assert results[0][0].text == "rc7-chunk"
    assert results[1][0].text == "rc8-chunk"


def test_hardware_match_prioritised_over_category_boost(db_session: Session) -> None:
    """Robot-config compatibility prioritises over the documental category boost.

    A chunk from the user's exact robot+controller (no category boost) must
    outrank a raw-closer, category-boosted chunk from different hardware —
    proving retrieval prioritises by hardware config, not category alone.
    """
    # Category-boosted (programming ×1.30) but for other hardware.
    other_hw = _make_manual(
        db_session,
        title="Programming (other robot)",
        storage_key="k/cat-other.pdf",
        categories=["programming"],
        robot_model="VS-060",  # mismatch ×0.70
        controller_version="RC8",  # mismatch ×0.85
    )
    # User's exact hardware, no category boost.
    my_hw = _make_manual(
        db_session,
        title="My robot manual",
        storage_key="k/my-hw.pdf",
        categories=[],
        robot_model="VP-6242",  # match ×1.30
        controller_version="RC7.2",  # match ×1.15
    )
    db_session.add(
        ManualChunk(
            manual_id=other_hw.id,
            chunk_index=0,
            page_number=1,
            text="other-hw-programming",
            embedding=_sim_vector(0.80),
        )
    )
    db_session.add(
        ManualChunk(
            manual_id=my_hw.id,
            chunk_index=0,
            page_number=1,
            text="my-hw",
            embedding=_sim_vector(0.70),
        )
    )
    db_session.commit()

    results = _retrieve_chunks(
        db_session,
        _unit_axis(0),
        _payload(robot_type="VP-6242", controller="RC7"),
        top_k=2,
    )

    # my-hw:    0.70 · (1.30·1.15)        = 1.05
    # other-hw: 0.80 · (0.70·0.85) · 1.30 = 0.62  (category boost not enough)
    assert results[0][0].text == "my-hw"
    assert results[1][0].text == "other-hw-programming"
    assert results[0][2] > results[1][2]
