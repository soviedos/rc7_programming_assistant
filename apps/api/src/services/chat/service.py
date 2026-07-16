"""RAG + Gemini chat service for RC7 programming assistant."""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import lru_cache

from google import genai
from google.genai import types
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import cast, select, text
from sqlalchemy.orm import Session

from src.api.v1.schemas.chat import ChatRequest, ChatResponse, ReferenceItem
from src.core.config import settings
from src.db.models import Manual, ManualChunk
from src.services.settings.service import (
    _DEFAULT_PAC_RULES,
    DEFAULT_SETTINGS,
    get_setting_value,
)

_logger = logging.getLogger(__name__)

# Model names and embedding dim are centralised in config (env-overridable).
_EMBED_MODEL = settings.gemini_embed_model
_EMBED_DIM = settings.gemini_embed_dim
_GEN_MODEL = settings.gemini_gen_model

# Fallback constants — used when DB settings are unavailable. Derived from the
# settings catalogue so the value has a single source.
_TOP_K = int(DEFAULT_SETTINGS["rag_top_k_chunks"][0])
_MAX_CTX_CHARS = int(DEFAULT_SETTINGS["rag_context_budget_chars"][0])
_TEMPERATURE = float(DEFAULT_SETTINGS["gemini_temperature"][0])
_MAX_TOKENS = int(DEFAULT_SETTINGS["gemini_max_tokens"][0])

# Number of nearest neighbours pulled from pgvector before the category/hardware
# re-ranking in Python. Wider than _TOP_K so the boost can promote relevant
# chunks that are not the very closest by raw cosine.
_VECTOR_CANDIDATE_POOL = int(DEFAULT_SETTINGS["rag_candidate_pool"][0])

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


@lru_cache(maxsize=8)
def _build_client(timeout_seconds: int) -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=timeout_seconds * 1000,  # SDK expects ms
        ),
    )


def _get_client(timeout_seconds: int | None = None) -> genai.Client:
    # Cached per timeout: a fresh Client per call would discard the underlying
    # httpx connection pool and force a TLS handshake on every Gemini request.
    timeout = (
        timeout_seconds if timeout_seconds is not None else settings.gemini_timeout_seconds
    )
    return _build_client(timeout)


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
    source_map: dict[str, tuple[Manual, int]],
) -> list[tuple[str, str, str]]:
    """Return the full source legend for the response.

    One entry **per SID present in ``source_map``**, ordered S1…Sn, as
    ``(source_id, title, page)``. The legend therefore covers EVERY ``S<n>`` that
    can appear as an inline ``' fuente: SX`` comment in the generated PAC code, so
    no cited ID is ever left unresolved.

    The model's own ``references`` array is intentionally ignored: the saved
    ``source_map`` is the single source of truth for ``SID → (manual, page)``.
    This mapping is persisted with the message so a SID never has to be re-decoded
    (and never invented) in a later turn.
    """

    def _order(sid: str) -> int:
        try:
            return int(sid[1:])
        except (ValueError, IndexError):
            return 0

    return [
        (sid, source_map[sid][0].title, str(source_map[sid][1]))
        for sid in sorted(source_map, key=_order)
    ]


def _prepend_source_legend(
    pac_code: str,
    source_map: dict[str, tuple[Manual, int]],
) -> str:
    """Prepend a PAC-comment source legend to non-empty ``pac_code``.

    Built **deterministically from ``source_map``** (never asked to the model) so
    the generated ``.pac`` file is self-contained outside the app. Uses the
    apostrophe comment syntax — valid in WinCaps III — so it never affects
    compilation. Only the SIDs present in ``source_map`` are included; if there
    is no code or no source, the code is returned unchanged.
    """
    legend = _resolve_references(source_map)
    if not pac_code or not legend:
        return pac_code

    block = ["' ─── Fuentes (trazabilidad) ───"]
    block += [f"' {sid} = {title}, pág. {page}" for sid, title, page in legend]
    block.append("' ──────────────────────────────")
    return "\n".join(block) + "\n" + pac_code


# ── Deterministic post-generation PAC linter ───────────────────────
#
# High-confidence, no-LLM fixes applied to pac_code before returning. Rules are
# anchored to a whole line so they only rewrite *statements*, never the same
# pattern inside a condition (IF ... = ON THEN, WAIT ... = ON). Indentation and
# the inline ``' fuente: SX`` comment are preserved. Extend ``_PAC_LINT_RULES``
# to add more patterns from the error taxonomy.


@dataclass(frozen=True)
class _PacLintRule:
    name: str
    pattern: re.Pattern[str]
    replacement: str  # may reference named groups via \g<name>


_PAC_LINT_RULES: list[_PacLintRule] = [
    # IO[x] = ON   (statement)  →  SET IO[x]
    _PacLintRule(
        name="io_assign_on_to_set",
        pattern=re.compile(
            r"^(?P<indent>[ \t]*)IO\[(?P<idx>[^\]]+)\][ \t]*=[ \t]*ON"
            r"(?P<comment>[ \t]+'.*)?[ \t]*$"
        ),
        replacement=r"\g<indent>SET IO[\g<idx>]\g<comment>",
    ),
    # IO[x] = OFF  (statement)  →  RESET IO[x]
    _PacLintRule(
        name="io_assign_off_to_reset",
        pattern=re.compile(
            r"^(?P<indent>[ \t]*)IO\[(?P<idx>[^\]]+)\][ \t]*=[ \t]*OFF"
            r"(?P<comment>[ \t]+'.*)?[ \t]*$"
        ),
        replacement=r"\g<indent>RESET IO[\g<idx>]\g<comment>",
    ),
    # MOVE J, …  →  MOVE P, …
    # "J" no es un método de interpolación: los válidos son P (PTP), L (lineal),
    # C (circular) y S (curva libre). Para un movimiento articular el correcto es
    # PTP, y el manual lo documenta como `MOVE P, J1`. WinCaps rechaza MOVE J con
    # "Wrong interpolation method designated. Kw(J)".
    _PacLintRule(
        name="move_invalid_interpolation_j",
        pattern=re.compile(r"^(?P<indent>[ \t]*)MOVE[ \t]+J[ \t]*,(?P<rest>.*)$"),
        replacement=r"\g<indent>MOVE P,\g<rest>",
    ),
    # J[x] = J(…)  →  J[x] = (…)      ·      J1 = J(…)  →  J1 = (…)
    # No existe constructor J(): el manual asigna con `J[0] = (10,20,30,40,50,60)`.
    # WinCaps rechaza la forma con constructor con "Type J data op('(')".
    _PacLintRule(
        name="joint_bogus_constructor",
        pattern=re.compile(
            r"^(?P<indent>[ \t]*)(?P<lhs>J(?:\[[^\]]+\]|[0-9]+)[ \t]*=[ \t]*)"
            r"J\((?P<args>.*)$"
        ),
        replacement=r"\g<indent>\g<lhs>(\g<args>",
    ),
]


def _lint_pac_code(pac_code: str) -> tuple[str, int]:
    """Apply deterministic high-confidence PAC fixes line by line.

    Returns ``(fixed_code, n_fixes)``. Each rule is line-anchored, so only whole
    statements are rewritten; an identical pattern embedded in an ``IF``/``WAIT``
    condition is left untouched. Indentation and any trailing ``' fuente: SX``
    comment are preserved.
    """
    if not pac_code:
        return pac_code, 0

    fixed: list[str] = []
    applied = 0
    for line in pac_code.split("\n"):
        for rule in _PAC_LINT_RULES:
            new_line, n = rule.pattern.subn(rule.replacement, line)
            if n:
                line = new_line
                applied += n
                break  # at most one statement-level rule matches a given line
        fixed.append(line)
    return "\n".join(fixed), applied


# ── Two-level PAC verification ─────────────────────────────────────
#
#  Level 1 — _lint_pac_code: DETERMINISTIC auto-fixes. High-confidence, no
#            context needed; it REWRITES the code and reports n_fixes.
#  Level 2 — _pac_advisories: SEMANTIC advisories. Context-dependent, so they are
#            only SHOWN to the user and NEVER modify the code (human review
#            required). Both levels keep an extensible rule list.

_MOTION_STMT = re.compile(r"^[ \t]*(?:MOVE|APPROACH|DEPART)\b")
# Step (pass) designator: @P or @<positive int>. Excludes @0 (decelerate/stop)
# and @E. A pass move does not stop precisely at the target.
_STEP_DESIGNATOR = re.compile(r"@(?:P|[1-9]\d*)(?![A-Za-z0-9])")
# Output actuation statement: SET IO[...] / RESET IO[...].
_IO_ACTUATE_STMT = re.compile(r"^[ \t]*(?:SET|RESET)[ \t]+IO\[")


def _next_significant_index(lines: list[str], i: int) -> int | None:
    """Index of the next statement after ``i``, skipping blanks and ``'`` comments."""
    for j in range(i + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped or stripped.startswith("'"):
            continue
        return j
    return None


def _advise_step_move_before_io(lines: list[str], i: int) -> str | None:
    """Step motion (@P / @<n>) immediately before actuating an output.

    A pass move does not decelerate to a precise stop, so toggling an output
    right after it may happen before the robot reaches the target point. Does not
    fire for @0 (which stops) nor when the next statement is another motion (a
    pass is legitimate there).
    """
    line = lines[i]
    if not _MOTION_STMT.match(line) or not _STEP_DESIGNATOR.search(line):
        return None
    nxt = _next_significant_index(lines, i)
    if nxt is None or not _IO_ACTUATE_STMT.match(lines[nxt]):
        return None
    return (
        f"Línea {i + 1}: movimiento de paso (@P) inmediatamente antes de actuar una "
        "salida; el robot puede no detenerse con precisión en el punto objetivo. Usa @0 "
        "para decelerar y parar en el objetivo si se requiere posicionamiento preciso "
        "(p. ej. recogida/depósito)."
    )


@dataclass(frozen=True)
class _PacAdvisoryRule:
    name: str
    # (lines, index) -> advisory message (with 1-based line number) or None.
    check: Callable[[list[str], int], str | None]


_PAC_ADVISORY_RULES: list[_PacAdvisoryRule] = [
    _PacAdvisoryRule(
        name="step_move_before_io", check=_advise_step_move_before_io
    ),
]


def _pac_advisories(pac_code: str) -> list[str]:
    """Level-2 semantic advisories (read-only) for ``pac_code``.

    Returns human-readable warnings; **never** modifies the code (unlike
    ``_lint_pac_code``). Line numbers are 1-based within ``pac_code``. Extend
    ``_PAC_ADVISORY_RULES`` to add more checks from the error taxonomy.
    """
    if not pac_code:
        return []
    lines = pac_code.split("\n")
    advisories: list[str] = []
    for i in range(len(lines)):
        for rule in _PAC_ADVISORY_RULES:
            msg = rule.check(lines, i)
            if msg:
                advisories.append(msg)
    return advisories


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


@dataclass(frozen=True)
class _ChatParams:
    top_k: int
    max_ctx: int
    temperature: float
    max_tokens: int
    timeout_seconds: int
    candidate_pool: int


def _load_chat_params(db: Session) -> _ChatParams:
    return _ChatParams(
        top_k=int(get_setting_value(db, "rag_top_k_chunks", str(_TOP_K))),
        max_ctx=int(
            get_setting_value(db, "rag_context_budget_chars", str(_MAX_CTX_CHARS))
        ),
        temperature=float(
            get_setting_value(db, "gemini_temperature", str(_TEMPERATURE))
        ),
        max_tokens=int(get_setting_value(db, "gemini_max_tokens", str(_MAX_TOKENS))),
        timeout_seconds=int(
            get_setting_value(
                db, "gemini_timeout_seconds", str(settings.gemini_timeout_seconds)
            )
        ),
        candidate_pool=int(
            get_setting_value(db, "rag_candidate_pool", str(_VECTOR_CANDIDATE_POOL))
        ),
    )


def _finalize_response(
    raw_text: str,
    source_map: dict[str, tuple[Manual, int]],
) -> tuple[str, str, list[tuple[str, str, str]], list[str]]:
    """Parse the Gemini payload and apply the deterministic post-generation steps.

    Returns (summary, pac_code, references, advisories). ``references`` are raw
    tuples so each caller can shape them for its own transport.
    """
    try:
        data = _parse_gemini_json(raw_text)
    except Exception:
        data = {"summary": raw_text, "pac_code": "", "references": []}

    summary = str(data.get("summary", "")).strip()
    pac_code = str(data.get("pac_code", "")).strip()

    pac_code, lint_fixes = _lint_pac_code(pac_code)
    if lint_fixes:
        _logger.info("PAC linter aplicó %d corrección(es) determinista(s)", lint_fixes)

    references = _resolve_references(source_map)
    # Make the .pac self-contained: prepend the deterministic source legend.
    pac_code = _prepend_source_legend(pac_code, source_map)

    advisories = _pac_advisories(pac_code)
    if advisories:
        _logger.info("PAC advisories: %d advertencia(s) semántica(s)", len(advisories))

    return summary or "Respuesta generada.", pac_code, references, advisories


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
) -> tuple[dict[str, tuple[Manual, int]], str, str]:
    """Run phases 1-3 of the RAG pipeline.

    Returns a 3-tuple: (source_map, system_prompt, phase4_message).
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

    return source_map, system_prompt, phase4_message


# ── Public entry point ─────────────────────────────────────────────


def generate_rag_response(db: Session, payload: ChatRequest) -> ChatResponse:
    """Four-phase RAG pipeline: HyDE → retrieval → context → structured response.

    Phase 1: Query → Gemini (prose, no JSON) for richer HyDE embedding.
    Phase 2: Embed (query + Phase 1 answer) → retrieve top-k manual chunks.
    Phase 3: Build RAG context from retrieved chunks.
    Phase 4: Final Gemini call with RAG context → structured JSON response.
    """
    params = _load_chat_params(db)

    source_map, system_prompt, phase4_message = _run_rag_phases(
        db,
        payload,
        top_k=params.top_k,
        max_ctx=params.max_ctx,
        temperature=params.temperature,
        max_tokens=params.max_tokens,
        timeout_seconds=params.timeout_seconds,
        candidate_pool=params.candidate_pool,
    )

    # ── Phase 4: Final structured call ────────────────────────────
    raw_text = _call_gemini(
        phase4_message,
        system_instruction=system_prompt,
        temperature=params.temperature,
        max_output_tokens=params.max_tokens,
        force_json=True,
        timeout_seconds=params.timeout_seconds,
    )

    summary, pac_code, references, advisories = _finalize_response(raw_text, source_map)

    return ChatResponse(
        summary=summary,
        pac_code=pac_code,
        references=[
            ReferenceItem(source_id=sid, title=title, page=page)
            for sid, title, page in references
        ],
        advisories=advisories,
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
    params = _load_chat_params(db)

    source_map, system_prompt, gemini_message = _run_rag_phases(
        db,
        payload,
        top_k=params.top_k,
        max_ctx=params.max_ctx,
        temperature=params.temperature,
        max_tokens=params.max_tokens,
        timeout_seconds=params.timeout_seconds,
        candidate_pool=params.candidate_pool,
    )

    # ── Phase 4: Stream final Gemini response ─────────────────────
    full_text = ""
    last_keepalive = time.time()

    for chunk_text in _call_gemini_stream(
        gemini_message,
        system_instruction=system_prompt,
        temperature=params.temperature,
        max_output_tokens=params.max_tokens,
        force_json=True,
        timeout_seconds=params.timeout_seconds,
    ):
        full_text += chunk_text
        now = time.time()
        if now - last_keepalive >= 15.0:
            yield ": keepalive\n\n"
            last_keepalive = now
        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_text})}\n\n"

    summary, pac_code, refs, advisories = _finalize_response(full_text, source_map)
    references = [
        {"source_id": sid, "title": title, "page": page} for sid, title, page in refs
    ]

    yield f"data: {json.dumps({'type': 'done', 'summary': summary, 'pac_code': pac_code, 'references': references, 'advisories': advisories})}\n\n"
