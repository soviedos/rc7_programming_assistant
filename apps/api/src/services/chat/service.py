"""RAG + Gemini chat service for RC7 programming assistant."""

from __future__ import annotations

import time
from collections.abc import Iterator

from google import genai
from google.genai import types
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import cast, select, text
from sqlalchemy.orm import Session

from src.api.v1.schemas.chat import ChatRequest, ChatResponse, ReferenceItem
from src.core.config import settings
from src.db.models import Manual, ManualChunk
from src.services.settings.service import _DEFAULT_PAC_RULES, get_setting_value

# Model names and embedding dim are centralised in config (env-overridable).
_EMBED_MODEL = settings.gemini_embed_model
_EMBED_DIM = settings.gemini_embed_dim
_GEN_MODEL = settings.gemini_gen_model

# Fallback constants — used when DB settings are unavailable.
_TOP_K = 6
_MAX_CTX_CHARS = 12_000
_TEMPERATURE = 0.7
_MAX_TOKENS = 8192

# Default number of nearest neighbours to pull from pgvector before applying the
# category/hardware re-ranking in Python (overridable via the rag_candidate_pool
# setting). Wider than _TOP_K so the boost can promote relevant chunks that are
# not the very closest by raw cosine.
_VECTOR_CANDIDATE_POOL = 50

# Category boost multipliers applied to cosine similarity scores.
# A value of 1.0 means no boost; >1.0 promotes chunks from that category.
_CATEGORY_BOOST: dict[str, float] = {
    "programming": 1.30,
    "startup": 1.15,
    "robot_specs": 1.05,
    "errors": 1.10,
}

# Hardware-compatibility multipliers. Each dimension of the manual's hardware
# metadata is compared against the user's robot configuration (ChatRequest):
#   * a match boosts the chunk (>1.0),
#   * a present-but-different value mildly penalises it (<1.0),
#   * missing metadata is neutral (1.0) so unlabelled chunks are never degraded.
_HW_ROBOT_MATCH_BOOST = 1.30
_HW_ROBOT_MISMATCH_PENALTY = 0.70
_HW_CONTROLLER_MATCH_BOOST = 1.15
_HW_CONTROLLER_MISMATCH_PENALTY = 0.85


# ── Helpers ────────────────────────────────────────────────────────


def _get_client(timeout_seconds: int | None = None) -> genai.Client:
    timeout = (
        timeout_seconds if timeout_seconds is not None else settings.gemini_timeout_seconds
    )
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=timeout * 1000,  # SDK expects ms
        ),
    )


def _embed_query(text_input: str, timeout_seconds: int | None = None) -> list[float]:
    client = _get_client(timeout_seconds)
    prefixed = f"task: search result | query: {text_input}"
    result = client.models.embed_content(
        model=_EMBED_MODEL,
        contents=prefixed,
        config=types.EmbedContentConfig(output_dimensionality=_EMBED_DIM),
    )
    return list(result.embeddings[0].values)


def _resolve_references(
    raw_refs: object,
    source_map: dict[str, tuple[Manual, int]],
) -> list[tuple[str, str]]:
    """Resolve model-cited source IDs to deduplicated (title, page) pairs.

    Extracts ``S<number>`` IDs from the model's ``references`` value, keeps only
    those present in ``source_map`` (discarding hallucinated IDs), and falls back
    to the full retrieved set when none of the cited IDs are valid.
    """
    import re

    cited: list[str] = []
    if isinstance(raw_refs, (list, tuple)):
        for item in raw_refs:
            cited.extend(re.findall(r"S\d+", str(item)))
    else:
        cited = re.findall(r"S\d+", str(raw_refs or ""))

    valid_ids = [sid for sid in cited if sid in source_map]
    if not valid_ids:
        valid_ids = list(source_map.keys())

    seen: set[str] = set()
    references: list[tuple[str, str]] = []
    for sid in valid_ids:
        manual, page = source_map[sid]
        key = f"{manual.title}:{page}"
        if key not in seen:
            seen.add(key)
            references.append((manual.title, str(page)))
    return references


def _normalize_hw(value: str | None) -> str:
    """Lowercase, alphanumeric-only form for tolerant hardware comparison.

    Collapses separator/format noise so e.g. ``"VS-060"`` and ``"VS060"`` —
    or ``"RC7"`` and ``"RC7.2"`` — compare on their meaningful tokens.
    """
    if not value:
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _hardware_compatibility_boost(manual: Manual, payload: ChatRequest) -> float:
    """Multiplier reflecting how well a manual's hardware matches the user's robot.

    Two independent dimensions are scored and multiplied:

    * **Robot model** — ``manual.robot_model`` vs ``payload.robot_type``.
    * **Controller / firmware** — ``manual.controller_version`` vs
      ``payload.controller`` (the controller_version string also carries the
      firmware revision, e.g. ``"RC7.2"``; the payload only specifies the
      controller family, so matching is done at that granularity).

    Each dimension yields a factor that is neutral (``1.0``) when the manual has
    no metadata for it — so chunks without configuration metadata keep their raw
    similarity and are never degraded — a boost when it matches, and a mild
    penalty when it is present but refers to different hardware.
    """
    robot_factor = 1.0
    manual_model = _normalize_hw(manual.robot_model)
    if manual_model:
        payload_model = _normalize_hw(payload.robot_type)
        matches = bool(payload_model) and (
            manual_model == payload_model
            or manual_model in payload_model
            or payload_model in manual_model
        )
        robot_factor = _HW_ROBOT_MATCH_BOOST if matches else _HW_ROBOT_MISMATCH_PENALTY

    controller_factor = 1.0
    manual_ctrl = _normalize_hw(manual.controller_version)
    if manual_ctrl:
        payload_ctrl = _normalize_hw(payload.controller)
        matches = bool(payload_ctrl) and (
            manual_ctrl.startswith(payload_ctrl) or payload_ctrl.startswith(manual_ctrl)
        )
        controller_factor = (
            _HW_CONTROLLER_MATCH_BOOST if matches else _HW_CONTROLLER_MISMATCH_PENALTY
        )

    return robot_factor * controller_factor


def _retrieve_chunks(
    db: Session,
    query_embedding: list[float],
    payload: ChatRequest,
    top_k: int = _TOP_K,
    candidate_pool: int = _VECTOR_CANDIDATE_POOL,
) -> list[tuple[ManualChunk, Manual, float]]:
    """Retrieve top-k chunks via pgvector cosine distance, then re-rank by score.

    Postgres orders a wide candidate pool by cosine distance using the ``<=>``
    operator (HNSW-accelerated through a halfvec cast, since pgvector caps
    ``vector`` HNSW indexes at 2000 dimensions). The pool is then re-ranked in
    Python to prioritise chunks whose manual matches the user's robot
    configuration and pick the top-k.

    Scoring formula (higher is better)::

        score(chunk) = cosine_similarity · hardware_factor · category_factor

    where:

    * ``cosine_similarity = 1 − (embedding <=> query)`` — the raw semantic match.
    * ``hardware_factor   = robot_factor · controller_factor`` — see
      :func:`_hardware_compatibility_boost`. Boosts manuals matching the
      payload's robot model / controller, mildly penalises manuals for other
      hardware, and is neutral (``1.0``) for chunks lacking hardware metadata so
      they are never degraded.
    * ``category_factor   = max(_CATEGORY_BOOST[c] for c in manual.categories)``
      (default ``1.0``) — a secondary nudge by document category.

    Incompatible chunks are demoted (soft "limiting") rather than hard-filtered,
    so the context is never left empty when no manual matches the exact hardware.
    """
    # Cast both sides to halfvec so the ORDER BY matches the HNSW index
    # expression and pgvector can use it instead of a full scan.
    half = HALFVEC(_EMBED_DIM)
    distance = cast(ManualChunk.embedding, half).cosine_distance(
        cast(query_embedding, half)
    )

    # Raise HNSW ef_search to at least the candidate pool so the index returns
    # enough neighbours for a meaningful re-rank (transaction-local; PG only).
    # SET LOCAL does not accept bind params; the value is an internal int.
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        ef_search = max(int(candidate_pool), 40)
        db.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))

    rows = db.execute(
        select(ManualChunk, Manual, distance.label("distance"))
        .join(Manual, Manual.id == ManualChunk.manual_id)
        .where(ManualChunk.embedding.isnot(None))
        .where(Manual.status == "indexed")
        .order_by(distance)
        .limit(candidate_pool)
    ).all()

    scored: list[tuple[ManualChunk, Manual, float]] = []
    for chunk, manual, distance_val in rows:
        # cosine distance (<=>) is 1 - cosine similarity.
        similarity = 1.0 - float(distance_val)
        hardware_factor = _hardware_compatibility_boost(manual, payload)
        category_factor = max(
            (_CATEGORY_BOOST.get(cat, 1.0) for cat in (manual.categories or [])),
            default=1.0,
        )
        scored.append((chunk, manual, similarity * hardware_factor * category_factor))

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


def _build_system_prompt(db: Session, payload: ChatRequest) -> str:
    io_expansion_line = ""
    if payload.has_io_expansion:
        io_expansion_line = (
            f"- Tarjeta expansión I/O: Sí "
            f"({payload.expansion_io_inputs} entradas / {payload.expansion_io_outputs} salidas)\n"
        )
    else:
        io_expansion_line = "- Tarjeta expansión I/O: No\n"

    pac_rules = get_setting_value(db, "system_prompt_pac", _DEFAULT_PAC_RULES)

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
        f"- Tool activo: Tool {payload.tool_number}\n\n" + pac_rules + "\n\n"
        "FORMATO DE RESPUESTA — CRÍTICO:\n"
        "Responde ÚNICAMENTE con un objeto JSON válido. Sin texto antes ni después del JSON.\n"
        "Campos:\n"
        "  summary   → texto plano explicativo. NUNCA incluyas código PAC aquí.\n"
        "  pac_code  → el programa PAC completo como cadena de texto plano, SIN backticks "
        "ni bloques markdown. Cadena vacía '' si no aplica.\n"
        "  references → array con los IDs de fuente realmente usados (p. ej. [\"S1\",\"S3\"]). "
        "Usa SOLO IDs que aparezcan en el CONTEXTO. Si no usaste ninguna fuente, devuelve [].\n\n"
        "TRAZABILIDAD — CRÍTICO:\n"
        "El CONTEXTO extraído de los manuales viene etiquetado con IDs [S1], [S2], …\n"
        "Cada instrucción o bloque PAC que provenga de una fuente DEBE llevar al final un "
        "comentario PAC con el ID de esa fuente, usando el apóstrofo (comentario válido en PAC), "
        "por ejemplo:\n"
        "  MOVE P, P1    ' fuente: S2\n"
        "NUNCA inventes IDs que no estén en el CONTEXTO; usa únicamente los IDs [SX] presentes.\n\n"
        "Ejemplo de respuesta CORRECTA:\n"
        '{"summary":"Programa pick and place que recoge en A y coloca en B.","pac_code":'
        '"#INCLUDE \\"dio_tab.h\\"\\nPROGRAM pickPlace\\n    TAKEARM\\n    MOVE P, P1    \' fuente: S1\\n'
        '    GIVEARM\\nEND","references":["S1"]}\n\n'
        "INCORRECTO — nunca pongas código PAC dentro del campo summary."
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
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Best-effort: extract first {...} block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                data = {"summary": cleaned, "pac_code": "", "references": []}
        else:
            # No JSON found at all — treat entire response as summary so the
            # safety net below can still extract pac_code from a code block.
            data = {"summary": cleaned, "pac_code": "", "references": []}

    # Safety net: if pac_code is empty but summary contains a PAC code block,
    # extract the code and strip it from the summary so the UI receives them
    # in the correct fields.
    pac_code = str(data.get("pac_code", "")).strip()
    summary = str(data.get("summary", "")).strip()
    if not pac_code and summary:
        code_match = re.search(
            r"```(?:pac)?\s*\n?(.*?)\n?```", summary, re.DOTALL | re.IGNORECASE
        )
        if code_match:
            data["pac_code"] = code_match.group(1).strip()
            data["summary"] = re.sub(
                r"```(?:pac)?\s*\n?.*?\n?```",
                "",
                summary,
                flags=re.DOTALL | re.IGNORECASE,
            ).strip()

    return data


# ── Gemini call helper ─────────────────────────────────────────────


def _call_gemini(
    message: str,
    system_instruction: str | None = None,
    *,
    temperature: float = _TEMPERATURE,
    max_output_tokens: int = _MAX_TOKENS,
    force_json: bool = False,
    timeout_seconds: int | None = None,
) -> str:
    """Call Gemini with retries; returns raw text or raises RuntimeError."""
    client = _get_client(timeout_seconds)
    gen_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        **(dict(response_mime_type="application/json") if force_json else {}),
    )
    last_exc: Exception | None = None
    for attempt in range(1, 4):
        try:
            resp = client.models.generate_content(
                model=_GEN_MODEL,
                contents=message,
                config=gen_config,
            )
            if resp.text is None:
                raise RuntimeError(
                    "Gemini devolvió una respuesta vacía (posible bloqueo de contenido o respuesta incompleta)."
                )
            return resp.text
        except Exception as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(2.0 * attempt)
    raise RuntimeError(
        f"Gemini no pudo generar una respuesta: {last_exc}"
    ) from last_exc


def _call_gemini_stream(
    message: str,
    system_instruction: str | None = None,
    *,
    temperature: float = _TEMPERATURE,
    max_output_tokens: int = _MAX_TOKENS,
    force_json: bool = False,
    timeout_seconds: int | None = None,
) -> Iterator[str]:
    """Yield raw text chunks from the Gemini streaming API."""
    client = _get_client(timeout_seconds)
    gen_config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        **(dict(response_mime_type="application/json") if force_json else {}),
    )
    for chunk in client.models.generate_content_stream(
        model=_GEN_MODEL,
        contents=message,
        config=gen_config,
    ):
        if chunk.text:
            yield chunk.text


# ── Shared prompt constants ────────────────────────────────────────

_PHASE1_SYSTEM = (
    "Eres un experto programador de robots industriales Denso RC7. "
    "Responde en español de forma técnica y detallada. "
    "Puedes incluir fragmentos de código PAC si son relevantes."
)

_NO_RAG_NOTE = (
    "AVISO: Los manuales del sistema aún no tienen embeddings generados, "
    "por lo que esta respuesta se basa en las reglas de sintaxis PAC incluidas "
    "en el prompt del sistema. Genera el código solicitado de la mejor forma "
    "posible usando esas reglas, e indica en el summary que no se usó contexto "
    "de manuales en esta respuesta."
)


# ── Shared RAG phases 1-3 ─────────────────────────────────────────


def _run_rag_phases(
    db: Session,
    payload: ChatRequest,
    *,
    top_k: int,
    max_ctx: int,
    temperature: float,
    max_tokens: int,
    timeout_seconds: int | None = None,
    candidate_pool: int = _VECTOR_CANDIDATE_POOL,
) -> tuple[list[str], dict[str, tuple[Manual, int]], str, str]:
    """Run phases 1-3 of the RAG pipeline.

    Returns a 4-tuple: (context_chunks, source_map, system_prompt, phase4_message).
    ``source_map`` maps stable source IDs ("S1", "S2", …) to (manual, page).
    ``phase4_message`` is already built for Phase 4 (RAG context or fallback).
    """
    system_prompt = _build_system_prompt(db, payload)

    # ── Phase 1: Direct Gemini call for HyDE embedding ────────────
    phase1_message = payload.prompt
    if payload.current_code.strip():
        phase1_message = (
            f"CÓDIGO PAC ACTUAL EN EL CANVAS:\n```pac\n{payload.current_code}\n```\n\n"
            f"CONSULTA DEL USUARIO:\n{payload.prompt}"
        )
    initial_answer = _call_gemini(
        phase1_message,
        system_instruction=_PHASE1_SYSTEM,
        temperature=temperature,
        max_output_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
    )

    # ── Phase 2: Embed (query + initial answer) → retrieve chunks ─
    query_embedding = _embed_query(
        f"{payload.prompt}\n{initial_answer[:600]}", timeout_seconds=timeout_seconds
    )
    retrieved = _retrieve_chunks(
        db, query_embedding, payload, top_k=top_k, candidate_pool=candidate_pool
    )

    # ── Phase 3: Build RAG context up to budget ───────────────────
    context_chunks: list[str] = []
    total_chars = 0
    source_map: dict[str, tuple[Manual, int]] = {}

    for chunk, manual, _score in retrieved:
        sid = f"S{len(source_map) + 1}"
        fragment = f"[{sid} | {manual.title} — pág. {chunk.page_number}]\n{chunk.text}"
        if total_chars + len(fragment) > max_ctx:
            break
        context_chunks.append(fragment)
        source_map[sid] = (manual, chunk.page_number)
        total_chars += len(fragment)

    # ── Build phase 4 message ─────────────────────────────────────
    if context_chunks:
        phase4_message = _build_user_message(payload, context_chunks)
    else:
        phase4_message = f"{_NO_RAG_NOTE}\n\nCONSULTA DEL USUARIO:\n{payload.prompt}"
        if payload.current_code.strip():
            phase4_message = (
                f"{_NO_RAG_NOTE}\n\n"
                f"CÓDIGO PAC ACTUAL EN EL CANVAS:\n```pac\n{payload.current_code}\n```\n\n"
                f"CONSULTA DEL USUARIO:\n{payload.prompt}"
            )

    return context_chunks, source_map, system_prompt, phase4_message


# ── Public entry point ─────────────────────────────────────────────


def generate_rag_response(db: Session, payload: ChatRequest) -> ChatResponse:
    """Four-phase RAG pipeline: HyDE → retrieval → context → structured response.

    Phase 1: Query → Gemini (prose, no JSON) for richer HyDE embedding.
    Phase 2: Embed (query + Phase 1 answer) → retrieve top-k manual chunks.
    Phase 3: Build RAG context from retrieved chunks.
    Phase 4: Final Gemini call with RAG context → structured JSON response.
    """
    top_k = int(get_setting_value(db, "rag_top_k_chunks", str(_TOP_K)))
    max_ctx = int(
        get_setting_value(db, "rag_context_budget_chars", str(_MAX_CTX_CHARS))
    )
    temperature = float(get_setting_value(db, "gemini_temperature", str(_TEMPERATURE)))
    max_tokens = int(get_setting_value(db, "gemini_max_tokens", str(_MAX_TOKENS)))
    timeout_seconds = int(
        get_setting_value(
            db, "gemini_timeout_seconds", str(settings.gemini_timeout_seconds)
        )
    )
    candidate_pool = int(
        get_setting_value(db, "rag_candidate_pool", str(_VECTOR_CANDIDATE_POOL))
    )

    _context_chunks, source_map, system_prompt, phase4_message = _run_rag_phases(
        db,
        payload,
        top_k=top_k,
        max_ctx=max_ctx,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
        candidate_pool=candidate_pool,
    )

    # ── Phase 4: Final structured call ────────────────────────────
    raw_text = _call_gemini(
        phase4_message,
        system_instruction=system_prompt,
        temperature=temperature,
        max_output_tokens=max_tokens,
        force_json=True,
        timeout_seconds=timeout_seconds,
    )

    try:
        data = _parse_gemini_json(raw_text)
    except Exception:
        data = {"summary": raw_text, "pac_code": "", "references": []}

    summary = str(data.get("summary", "")).strip()
    pac_code = str(data.get("pac_code", "")).strip()

    references = [
        ReferenceItem(title=title, page=page)
        for title, page in _resolve_references(data.get("references"), source_map)
    ]

    return ChatResponse(
        summary=summary or "Respuesta generada.",
        pac_code=pac_code,
        references=references,
    )


def stream_rag_response(
    db: Session,
    payload: ChatRequest,
) -> Iterator[str]:
    """Run the 4-phase RAG pipeline streaming Phase 4 tokens as SSE strings.

    Yields SSE-formatted strings: keepalive comments, ``chunk`` data events,
    and a final ``done`` data event containing the parsed summary, pac_code
    and references.  Raises RuntimeError on pipeline failure (the caller is
    responsible for catching it and emitting an ``error`` event).
    """
    import json

    top_k = int(get_setting_value(db, "rag_top_k_chunks", str(_TOP_K)))
    max_ctx = int(
        get_setting_value(db, "rag_context_budget_chars", str(_MAX_CTX_CHARS))
    )
    temperature = float(get_setting_value(db, "gemini_temperature", str(_TEMPERATURE)))
    max_tokens = int(get_setting_value(db, "gemini_max_tokens", str(_MAX_TOKENS)))
    timeout_seconds = int(
        get_setting_value(
            db, "gemini_timeout_seconds", str(settings.gemini_timeout_seconds)
        )
    )
    candidate_pool = int(
        get_setting_value(db, "rag_candidate_pool", str(_VECTOR_CANDIDATE_POOL))
    )

    _context_chunks, source_map, system_prompt, gemini_message = _run_rag_phases(
        db,
        payload,
        top_k=top_k,
        max_ctx=max_ctx,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
        candidate_pool=candidate_pool,
    )

    # ── Phase 4: Stream final Gemini response ─────────────────────
    full_text = ""
    last_keepalive = time.time()

    for chunk_text in _call_gemini_stream(
        gemini_message,
        system_instruction=system_prompt,
        temperature=temperature,
        max_output_tokens=max_tokens,
        force_json=True,
        timeout_seconds=timeout_seconds,
    ):
        full_text += chunk_text
        now = time.time()
        if now - last_keepalive >= 15.0:
            yield ": keepalive\n\n"
            last_keepalive = now
        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_text})}\n\n"

    try:
        data = _parse_gemini_json(full_text)
    except Exception:
        data = {"summary": full_text, "pac_code": "", "references": []}

    summary = str(data.get("summary", "")).strip()
    pac_code = str(data.get("pac_code", "")).strip()

    references = [
        {"title": title, "page": page}
        for title, page in _resolve_references(data.get("references"), source_map)
    ]

    yield f"data: {json.dumps({'type': 'done', 'summary': summary or 'Respuesta generada.', 'pac_code': pac_code, 'references': references})}\n\n"
