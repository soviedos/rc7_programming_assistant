from datetime import datetime

from pydantic import BaseModel, Field


class SettingRead(BaseModel):
    id: int
    key: str
    value: str
    description: str
    updated_at: datetime


class SettingUpdate(BaseModel):
    value: str = Field(min_length=0)


class SettingsBulkEntry(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    value: str


class SettingsBulkUpdate(BaseModel):
    updates: list[SettingsBulkEntry]


class SettingsResponse(BaseModel):
    items: list[SettingRead]
