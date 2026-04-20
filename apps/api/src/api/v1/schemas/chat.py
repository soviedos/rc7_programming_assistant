from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    robot_type: str = "6-axis"
    controller: str = "RC7"
    io_profile: str = "default"


class ReferenceItem(BaseModel):
    title: str
    page: str


class ChatResponse(BaseModel):
    summary: str
    pac_code: str
    references: list[ReferenceItem]
