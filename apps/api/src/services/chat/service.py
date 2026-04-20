from src.api.v1.schemas.chat import ChatRequest, ChatResponse, ReferenceItem


def build_placeholder_response(payload: ChatRequest) -> ChatResponse:
    code = "\n".join(
        [
            "PROGRAM SAMPLE_RC7",
            "  TAKEARM",
            "  MOTOR ON",
            "  SPEED 40",
            "  MOVE P, P_HOME",
            "  ; TODO: sustituir por generacion real con Gemini y retrieval",
            "END",
        ]
    )

    return ChatResponse(
        summary=(
            f"Respuesta de ejemplo para robot {payload.robot_type} "
            f"con controlador {payload.controller}."
        ),
        pac_code=code,
        references=[
            ReferenceItem(
                title="Programmer's Manual I",
                page="3-24",
            )
        ],
    )
