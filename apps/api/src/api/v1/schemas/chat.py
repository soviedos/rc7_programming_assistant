from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

HandType = Literal["pneumatic_single", "pneumatic_double", "electric", "none"]
InstallType = Literal["floor", "ceiling", "wall"]


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    # Robot configuration
    robot_type: str = "VP-6242"
    controller: str = "RC7"
    io_profile: str = "default"
    payload_kg: float = 2.0
    tool_number: int = 1
    max_speed_pct: int = 100
    # Extended sidebar fields
    hand_type: HandType = "none"
    install_type: InstallType = "floor"
    has_io_expansion: bool = False
    expansion_io_inputs: int = 0
    expansion_io_outputs: int = 0
    # Current code in the canvas (optional — sent for context when editing)
    current_code: str = ""


class ReferenceItem(BaseModel):
    source_id: str  # stable traceability ID for this response, e.g. "S2"
    title: str
    page: str


class ChatResponse(BaseModel):
    summary: str
    pac_code: str
    references: list[ReferenceItem]
    # Level-2 semantic warnings shown to the user; they never modify the code.
    advisories: list[str] = []


class ChatHistoryItemResponse(BaseModel):
    id: int
    prompt: str
    summary: str
    pac_code: str
    references: list[ReferenceItem]
    advisories: list[str] = []
    robot_config: dict
    entry_type: str
    created_at: datetime


class ChatHistoryListResponse(BaseModel):
    items: list[ChatHistoryItemResponse]
    total: int
