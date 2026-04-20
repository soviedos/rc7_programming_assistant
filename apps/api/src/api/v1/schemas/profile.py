from typing import Literal

from pydantic import BaseModel, Field

PreferredLanguage = Literal["es", "en"]


class ProfileSettings(BaseModel):
    preferred_language: PreferredLanguage = "es"


class ProfileResponse(BaseModel):
    email: str
    display_name: str
    settings: ProfileSettings


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    settings: ProfileSettings


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=8, max_length=16)


class ProfileActionResponse(BaseModel):
    success: bool
    message: str
