"""RAG + Gemini chat service for RC7 programming assistant."""

from __future__ import annotations

import math
import time
from typing import Sequence

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.v1.schemas.chat import ChatRequest, ChatResponse, ReferenceItem
from src.core.config import settings
from src.db.models.manual import Manual
from src.db.models.manual_chunk import ManualChunk

_EMBED_MODEL = "gemini-embedding-001"
_GEN_MODEL = "gemini-2.5-flash"
_TOP_K = 6  # number of chunks to retrieve
_MAX_CTX_CHARS = 12_000  # character budget for context passed to Gemini

# Category boost multipliers applied to cosine similarity scores.
# A value of 1.0 means no boost; >1.0 promotes chunks from that category.
_CATEGORY_BOOST: dict[str, float] = {
    "programming": 1.30,
    "startup": 1.15,
    "robot_specs": 1.05,
    "errors": 1.10,
}


# ── Helpers ────────────────────────────────────────────────────────


def _get_client() -> genai.Client:
    import httpx

    return genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=settings.gemini_timeout_seconds * 1000,  # SDK expects ms
        ),
    )


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
        boost = max(
            (_CATEGORY_BOOST.get(cat, 1.0) for cat in (manual.categories or [])),
            default=1.0,
        )
        scored.append((chunk, manual, sim * boost))

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
        "Cuando generes código PAC debes seguir ESTRICTAMENTE la sintaxis real del lenguaje PAC "
        "tal como aparece en los programas de Denso Wincaps III (Capítulo 9 del manual RC7).\n\n"
        "ESTRUCTURA Y SINTAXIS REAL DE UN PROGRAMA PAC:\n\n"
        "1. DIRECTIVAS DE PREPROCESADOR (opcionales, van antes de PROGRAM):\n"
        '   #INCLUDE "dio_tab.h"   \'Lee el archivo de macros de E/S digitales\n'
        '   #INCLUDE "var_tab.h"   \'Lee el archivo de macros de variables\n'
        "   #DEFINE appLen  100    'Define una constante (nombre y valor son equivalentes)\n\n"
        "2. DECLARACIÓN DEL PROGRAMA:\n"
        "   PROGRAM pro1\n\n"
        "3. CUERPO PRINCIPAL: instrucciones terminadas con END.\n\n"
        "4. SUBRUTINAS: definidas DESPUÉS del END con el formato:\n"
        "   *NombreSubrutina:\n"
        "       <instrucciones>\n"
        "   RETURN\n\n"
        "REGLAS CRÍTICAS DE SINTAXIS (incumplirlas genera errores de compilación o comportamiento incorrecto):\n\n"
        "- CONTROL DEL BRAZO: se obtiene con TAKEARM y se libera con GIVEARM (NO usar FREEARM).\n"
        "- MOTORES: MOTOR ON activa los motores; MOTOR OFF los apaga. Se usan según el contexto; "
        "en programas modulares el control de motores puede estar en el programa principal o en rutinas de init.\n"
        "- MOVIMIENTO:\n"
        "    * Movimiento PTP (articular): MOVE P, P[pHome], S=50  (S= especifica % de velocidad interna)\n"
        "    * Movimiento lineal relativo: MOVE P, @P P[pPick]  (@ indica relativo al punto actual)\n"
        "    * JUMP para trayectorias articulares largas entre puntos alejados: JUMP P[pPrePick]\n"
        "    * Los puntos se referencian como macros: P[pHome], P[pPick], P[pPlace], etc.\n"
        "      (definidos en var_tab.h) o como P0, P1, P10, etc.\n"
        "- VARIABLES:\n"
        "    * Enteras:    I[iPartsId], I[iCount]  (macros de var_tab.h)\n"
        "    * Reales:     F[fDelay], F[fSpeed]\n"
        "    * Cadenas:    C[cMsg]\n"
        "    * NO declarar variables locales con DIM salvo casos especiales; usar macros.\n"
        "- E/S DIGITALES:\n"
        "    * Las señales se nombran con macros: ioParts, ioPartsAck, ioGripperOpen, etc.\n"
        "    * Para esperar entrada y activar salida: CALL dioWaitAndSet(ioIn, ioOut)\n"
        "    * Para activar salida y esperar confirmación: CALL dioSetAndWait(ioOut, ioAck)\n"
        "    * Asignación directa: IO[ioGripperOpen] = ON  o  IO[ioGripperOpen] = OFF\n"
        "- LLAMADAS:\n"
        "    * Programa externo: CALL pro2  (sin asterisco)\n"
        "    * Subrutina interna: GOSUB *PlacePartsA  (con asterisco, SIN dos puntos al llamar)\n"
        "    * La DEFINICIÓN de la subrutina sí lleva dos puntos: *PlacePartsA:\n"
        "- CONTROL DE FLUJO:\n"
        "    * Condicional múltiple: SELECT CASE I[iPartsId]\n"
        "                               CASE -1\n"
        "                                   CALL dioSetAndWait(ioErrQR, ioErrQRAck)\n"
        "                               CASE 1\n"
        "                                   GOSUB *PlacePartsA\n"
        "                               CASE 2, 3\n"
        "                                   GOSUB *PlacePartsBC\n"
        "                           END SELECT\n"
        "- VELOCIDAD: SPEED 100 establece velocidad interna al 100%; también ACCEL y DECEL.\n"
        "- COMENTARIOS: siempre inline al final de la línea con comilla simple: TAKEARM  'Obtiene semáforo del brazo\n"
        "  NO usar bloques de comentarios con ' --- encabezado --- ni líneas de comentario solas salvo\n"
        "  cuando sea necesario para aclarar lógica compleja.\n\n"
        "Ejemplo de programa real correcto:\n"
        '  #INCLUDE "dio_tab.h"                           \'Lee macros de E/S\n'
        '  #INCLUDE "var_tab.h"                           \'Lee macros de variables\n'
        "  #DEFINE appLen  100                            'Define longitud de aproximación\n\n"
        "  PROGRAM pro1\n"
        "      TAKEARM                                    'Obtiene semáforo del brazo\n"
        "      MOVE P, P[pHome], S=50                     'Mueve a HOME al 50% de velocidad interna\n"
        "      SPEED 100                                  'Establece velocidad al 100%\n"
        "      CALL dioWaitAndSet(ioParts, ioPartsAck)    'Verifica suministro de piezas\n"
        "      CALL pro2                                  'Lee el código QR\n"
        "      SELECT CASE I[iPartsId]\n"
        "          CASE -1\n"
        "              CALL dioSetAndWait(ioErrQR, ioErrQRAck) 'Salida de error\n"
        "          CASE 1\n"
        "              GOSUB *PlacePartsA                 'Procesa pieza A\n"
        "          CASE 2, 3\n"
        "              GOSUB *PlacePartsBC                'Procesa piezas B y C\n"
        "      END SELECT\n"
        "      CALL dioSetAndWait(ioComplete, ioCompleteAck) 'Señal de fin de movimiento\n"
        "      GIVEARM                                    'Libera semáforo del brazo\n"
        "  END\n\n"
        "ARCHIVOS DE INCLUDE — REGLA OBLIGATORIA:\n"
        'Cuando el programa use #INCLUDE "dio_tab.h" o #INCLUDE "var_tab.h", DEBES generar '
        "el contenido de esos archivos en el mismo campo pac_code, usando este formato de separación:\n\n"
        "' ================================================================\n"
        "' ARCHIVO: dio_tab.h\n"
        "' ================================================================\n"
        "#DEFINE ioGripperOpen    0   'Salida: abrir gripper\n"
        "#DEFINE ioGripperClose   1   'Salida: cerrar gripper\n"
        "...(todas las señales usadas en el programa)\n\n"
        "' ================================================================\n"
        "' ARCHIVO: var_tab.h\n"
        "' ================================================================\n"
        "#DEFINE pHome     0   'Punto de posición HOME\n"
        "#DEFINE pPick     1   'Punto de recogida\n"
        "...(todos los puntos y variables usados en el programa)\n\n"
        "' ================================================================\n"
        "' ARCHIVO: <nombre_programa>.pac\n"
        "' ================================================================\n"
        '#INCLUDE "dio_tab.h"\n'
        '#INCLUDE "var_tab.h"\n'
        "PROGRAM <nombre>\n"
        "...\n"
        "END\n\n"
        "Los tres bloques van en el mismo string pac_code, en ese orden. "
        "Cada #DEFINE debe incluir el número de señal/índice real y un comentario descriptivo. "
        "Las señales de E/S deben corresponder al perfil I/O configurado del robot.\n\n"
        "RESTRICCIONES:\n"
        "- Genera código PAC libremente usando las reglas de sintaxis de este prompt "
        "más el contexto de manuales. Componer secuencias lógicas (pick & place, "
        "inicialización, manejo de E/S) es parte de tu tarea aunque el manual no las "
        "muestre completas.\n"
        "- NUNCA inventes números de página, códigos de error numéricos ni valores de "
        "temporización que no aparezcan en el contexto. Si un dato específico no está, "
        "usa un comentario indicando que debe configurarse ('ajustar según aplicación').\n"
        "- NUNCA incluyas referencias bibliográficas en el JSON; el campo 'references' "
        "debe quedar siempre como array vacío []. Las referencias las gestiona el sistema.\n\n"
        "Reglas adicionales:\n"
        "1. NUNCA omitas el PROGRAM ni el END.\n"
        "2. Usa GIVEARM (no FREEARM) para liberar el brazo.\n"
        "3. Usa macros para puntos y variables (P[pHome], I[iCount]) en lugar de literales P0, I[00].\n"
        "4. Adapta las E/S al perfil I/O del robot indicado en la configuración.\n\n"
        "Para troubleshooting: diagnostica paso a paso. Si el contexto incluye el código "
        "de error o la sección del manual, cítalos; si no, explica el diagnóstico general.\n\n"
        "FORMATO DE RESPUESTA — CRÍTICO:\n"
        "Responde ÚNICAMENTE con un objeto JSON válido. Sin texto antes ni después del JSON.\n"
        "Campos:\n"
        "  summary   → texto plano explicativo. NUNCA incluyas código PAC aquí.\n"
        "  pac_code  → el programa PAC completo como cadena de texto plano, SIN backticks "
        "ni bloques markdown. Cadena vacía '' si no aplica.\n"
        "  references → siempre array vacío [].\n\n"
        "Ejemplo de respuesta CORRECTA:\n"
        '{"summary":"Programa pick and place que recoge en A y coloca en B.","pac_code":'
        '"#INCLUDE \\"dio_tab.h\\"\\nPROGRAM pickPlace\\n    TAKEARM\\n    GIVEARM\\nEND","references":[]}\n\n'
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
            data = json.loads(match.group(0))
        else:
            raise

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
    # Use a simplified system prompt (no JSON format) so the answer reads
    # as natural prose — this produces much better embeddings for HyDE retrieval.
    system_prompt = _build_system_prompt(payload)
    phase1_system = (
        "Eres un experto programador de robots industriales Denso RC7. "
        "Responde en español de forma técnica y detallada. "
        "Puedes incluir fragmentos de código PAC si son relevantes."
    )
    phase1_message = payload.prompt
    if payload.current_code.strip():
        phase1_message = (
            f"CÓDIGO PAC ACTUAL EN EL CANVAS:\n```pac\n{payload.current_code}\n```\n\n"
            f"CONSULTA DEL USUARIO:\n{payload.prompt}"
        )
    initial_answer = _call_gemini(phase1_message, system_instruction=phase1_system)

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
        # No embedded chunks available yet (embeddings not generated or DB empty).
        # Fall back to system-prompt-only generation so the assistant still works.
        # The summary will note the absence of manual context.
        no_rag_note = (
            "AVISO: Los manuales del sistema aún no tienen embeddings generados, "
            "por lo que esta respuesta se basa en las reglas de sintaxis PAC incluidas "
            "en el prompt del sistema. Genera el código solicitado de la mejor forma "
            "posible usando esas reglas, e indica en el summary que no se usó contexto "
            "de manuales en esta respuesta."
        )
        fallback_message = f"{no_rag_note}\n\nCONSULTA DEL USUARIO:\n{payload.prompt}"
        if payload.current_code.strip():
            fallback_message = (
                f"{no_rag_note}\n\n"
                f"CÓDIGO PAC ACTUAL EN EL CANVAS:\n```pac\n{payload.current_code}\n```\n\n"
                f"CONSULTA DEL USUARIO:\n{payload.prompt}"
            )
        raw_text = _call_gemini(fallback_message, system_instruction=system_prompt)

    # ── Parse structured JSON ──────────────────────────────────────
    try:
        data = _parse_gemini_json(raw_text)
    except Exception:
        data = {"summary": raw_text, "pac_code": "", "references": []}

    summary = str(data.get("summary", "")).strip()
    pac_code = str(data.get("pac_code", "")).strip()

    # ── Build references — only from RAG chunks, never from Gemini ──
    seen_titles: set[str] = set()
    references: list[ReferenceItem] = []

    for _manual, page in reference_map.values():
        key = f"{_manual.title}:{page}"
        if key not in seen_titles:
            seen_titles.add(key)
            references.append(ReferenceItem(title=_manual.title, page=str(page)))

    return ChatResponse(
        summary=summary or "Respuesta generada.",
        pac_code=pac_code,
        references=references,
    )
