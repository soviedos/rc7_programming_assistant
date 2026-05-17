from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginOptionsResponse(BaseModel):
    providers: list[str]
    note: str


RoleName = Literal["admin", "user"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class SessionResponse(BaseModel):
    email: EmailStr
    display_name: str
    role: RoleName
    available_roles: list[RoleName]


class RoleSwitchRequest(BaseModel):
    role: RoleName


class LogoutResponse(BaseModel):
    success: bool
