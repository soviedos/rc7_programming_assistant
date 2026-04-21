"""RAG + Gemini chat service for RC7 programming assistant."""

from __future__ import annotations

import math
import time
from typing import Sequence

from google import genai
from google.genai import types
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.api.v1.schemas.chat import ChatRequest, ChatResponse, ReferenceItem
from src.core.config import settings
from src.db.models.manual import Manual
from src.db.models.manual_chunk import ManualChunk

_EMBED_MODEL = "gemini-embedding-001"
_GEN_MODEL = "gemini-2.5-flash"
_TOP_K = 6  # number of chunks to retrieve
_MAX_CTX_CHARS = 12_000  # character budget for context passed to Gemini


# ── Helpers ────────────────────────────────────────────────────────


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


def _embed_query(text_input: str) -> list[float]:
    client = _get_client()
    result = client.models.embed_content(
        model=_EMBED_MODEL,
        contents=text_input,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return list(result.embeddings[0].values)


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _retrieve_chunks(
    db: Session,
    query_embedding: list[float],
    top_k: int = _TOP_K,
) -> list[tuple[ManualChunk, Manual, float]]:
    """Retrieve top-k chunks with cosine similarity using PostgreSQL REAL[]."""
    # Fetch all chunks that have an embedding (limit to a reasonable cap to avoid OOM)
    rows = db.execute(
        select(ManualChunk, Manual)
        .join(Manual, Manual.id == ManualChunk.manual_id)
        .where(ManualChunk.embedding.isnot(None))
        .limit(5000)
    ).all()

    scored: list[tuple[ManualChunk, Manual, float]] = []
    for chunk, manual in rows:
        if not chunk.embedding:
            continue
        sim = _cosine_similarity(query_embedding, chunk.embedding)
        scored.append((chunk, manual, sim))

    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:top_k]


_HAND_TYPE_LABELS = {
    "pneumatic_single": "Neumática simple",
    "pneumatic_double": "Neumática doble",
    "electric": "Eléctrica",
    "none": "Sin mano",
}

_INSTALL_TYPE_LABELS = {
    "floor": "Piso",
    "ceiling": "Techo",
    "wall": "Pared",
}


def _build_system_prompt(payload: ChatRequest) -> str:
    io_expansion_line = ""
    if payload.has_io_expansion:
        io_expansion_line = (
            f"- Tarjeta expansión I/O: Sí "
            f"({payload.expansion_io_inputs} entradas / {payload.expansion_io_outputs} salidas)\n"
        )
    else:
        io_expansion_line = "- Tarjeta expansión I/O: No\n"

    return (
        "Eres un experto programador de robots industriales Denso con controlador RC7. "
        "Respondes en español con precisión técnica. "
        "Tu tarea es ayudar al usuario con programación PAC (lenguaje de Denso Wincaps III), "
        "resolución de problemas y configuración del robot.\n\n"
        f"Configuración del robot en uso:\n"
        f"- Modelo: {payload.robot_type}\n"
        f"- Controlador: {payload.controller}\n"
        f"- Perfil I/O: {payload.io_profile}\n"
        f"- Carga operativa: {payload.payload_kg} kg\n"
        f"- Tipo de manipulador: {_HAND_TYPE_LABELS.get(payload.hand_type, payload.hand_type)}\n"
        f"- Tipo de instalación: {_INSTALL_TYPE_LABELS.get(payload.install_type, payload.install_type)}\n"
        + io_expansion_line
        + f"- Velocidad máxima: {payload.max_speed_pct}%\n"
        f"- Tool activo: Tool {payload.tool_number}\n\n"
        "Cuando generes código PAC:\n"
        "1. Usa los comandos correctos del manual (TAKEARM, MOTOR ON/OFF, SPEED, MOVE, etc.).\n"
        "2. Incluye comentarios en cada bloque lógico.\n"
        "3. Maneja siempre HOME al inicio y al final.\n"
        "4. El bloque de código PAC debe estar EXCLUSIVAMENTE dentro de ```pac ... ```.\n\n"
        "Para troubleshooting: diagnostica paso a paso, menciona el código de error si aplica "
        "y la sección del manual donde se describe la solución.\n\n"
        "Responde SIEMPRE con este formato JSON (sin markdown adicional fuera del JSON):\n"
        "{\n"
        '  "summary": "explicación breve de lo que hace o diagnóstico",\n'
        '  "pac_code": "código PAC completo (vacío si no aplica)",\n'
        '  "references": [{"title": "nombre del manual", "page": "N-NN o sección"}]\n'
        "}"
    )


def _build_user_message(payload: ChatRequest, context_chunks: list[str]) -> str:
    ctx = "\n\n---\n\n".join(context_chunks)
    code_section = ""
    if payload.current_code.strip():
        code_section = (
            f"CÓDIGO PAC ACTUAL EN EL CANVAS (el usuario puede estar editando o consultando sobre él):\n"
            f"```pac\n{payload.current_code}\n```\n\n---\n\n"
        )
    return (
        f"{code_section}"
        f"CONTEXTO EXTRAÍDO DE LOS MANUALES RC7:\n{ctx}\n\n"
        f"---\n\n"
        f"CONSULTA DEL USUARIO:\n{payload.prompt}"
    )


def _parse_gemini_json(raw: str) -> dict:
    """Extract the JSON object from the raw Gemini response text."""
    import json
    import re

    # Strip possible markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Best-effort: extract first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


# ── Gemini call helper ─────────────────────────────────────────────


def _call_gemini(
    message: str,
    system_instruction: str | None = None,
) -> str:
    """Call Gemini with retries; returns raw text or raises RuntimeError."""
    client = _get_client()
    config = (
        types.GenerateContentConfig(system_instruction=system_instruction)
        if system_instruction
        else None
    )
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            resp = client.models.generate_content(
                model=_GEN_MODEL,
                contents=message,
                config=config,
            )
            return resp.text
        except Exception as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(2.0 * attempt)
    raise RuntimeError(
        f"Gemini no pudo generar una respuesta: {last_exc}"
    ) from last_exc


# ── Public entry point ─────────────────────────────────────────────


def generate_rag_response(db: Session, payload: ChatRequest) -> ChatResponse:
    """Two-phase pipeline: Gemini first → RAG retrieval (HyDE) → structured response.

    Phase 1: The user query goes directly to Gemini (no RAG context) so the
             model answers from its own knowledge immediately.
    Phase 2: Query + Gemini's initial answer are embedded together and used to
             retrieve the most relevant manual chunks (Hypothetical Document
             Embeddings — HyDE).  This finds better matches than embedding the
             bare question.
    Phase 3: If chunks were found, a second Gemini call is made with the RAG
             context to produce the final structured JSON response.  If the DB
             has no embeddings yet, Phase 1's answer is parsed directly.
    """
    # ── Phase 1: Direct Gemini call (no RAG) ──────────────────────
    system_prompt = _build_system_prompt(payload)
    phase1_message = payload.prompt
    if payload.current_code.strip():
        phase1_message = (
            f"CÓDIGO PAC ACTUAL EN EL CANVAS:\n```pac\n{payload.current_code}\n```\n\n"
            f"CONSULTA DEL USUARIO:\n{payload.prompt}"
        )
    initial_answer = _call_gemini(phase1_message, system_instruction=system_prompt)

    # ── Phase 2: Embed (query + initial answer) → retrieve chunks ─
    embed_input = f"{payload.prompt}\n{initial_answer[:600]}"
    query_embedding = _embed_query(embed_input)
    retrieved = _retrieve_chunks(db, query_embedding, top_k=_TOP_K)

    # ── Phase 3: Build RAG context ────────────────────────────────
    context_chunks: list[str] = []
    total_chars = 0
    reference_map: dict[int, tuple[Manual, int]] = {}

    for chunk, manual, _score in retrieved:
        fragment = f"[{manual.title} — pág. {chunk.page_number}]\n{chunk.text}"
        if total_chars + len(fragment) > _MAX_CTX_CHARS:
            break
        context_chunks.append(fragment)
        reference_map[chunk.id] = (manual, chunk.page_number)
        total_chars += len(fragment)

    # ── Phase 4: Final structured call with RAG context ───────────
    if context_chunks:
        # RAG has relevant documentation — ground the answer in it
        user_message = _build_user_message(payload, context_chunks)
        raw_text = _call_gemini(user_message, system_instruction=system_prompt)
    else:
        # No embeddings/chunks available yet — ask Gemini for structured JSON
        # directly using Phase 1's answer as additional context
        fallback_message = (
            f"RESPUESTA PREVIA (sin contexto de manuales):\n{initial_answer}\n\n"
            f"---\n\nCONSULTA DEL USUARIO:\n{payload.prompt}\n\n"
            "Reformatea la respuesta anterior al JSON estructurado solicitado."
        )
        raw_text = _call_gemini(fallback_message, system_instruction=system_prompt)

    # ── Parse structured JSON ──────────────────────────────────────
    try:
        data = _parse_gemini_json(raw_text)
    except Exception:
        data = {"summary": raw_text, "pac_code": "", "references": []}

    summary = str(data.get("summary", "")).strip()
    pac_code = str(data.get("pac_code", "")).strip()

    # ── Build references ───────────────────────────────────────────
    seen_titles: set[str] = set()
    references: list[ReferenceItem] = []

    for _manual, page in reference_map.values():
        key = f"{_manual.title}:{page}"
        if key not in seen_titles:
            seen_titles.add(key)
            references.append(ReferenceItem(title=_manual.title, page=str(page)))

    for ref in data.get("references", []):
        if isinstance(ref, dict):
            title = str(ref.get("title", "")).strip()
            page = str(ref.get("page", "")).strip()
            key = f"{title}:{page}"
            if title and key not in seen_titles:
                seen_titles.add(key)
                references.append(ReferenceItem(title=title, page=page))

    return ChatResponse(
        summary=summary or "Respuesta generada.",
        pac_code=pac_code,
        references=references,
    )
