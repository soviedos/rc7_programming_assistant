from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import EmailStr, Field


class AdminStatusResponse(BaseModel):
    manuals_indexed: int
    active_users: int
    pending_jobs: int


UserRole = Literal["admin", "user"]


class AdminUserResponse(BaseModel):
    id: int
    email: EmailStr
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]
    total: int


class AdminUserCreateRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=16)
    role: UserRole = "user"
    is_active: bool = True


class AdminUserUpdateRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    role: UserRole
    is_active: bool
    password: str | None = Field(default=None, min_length=8, max_length=16)


class RolePermissionResponse(BaseModel):
    id: int
    key: str
    name: str
    description: str
    admin: bool
    user: bool


class RolePermissionListResponse(BaseModel):
    items: list[RolePermissionResponse]


class RolePermissionCreateRequest(BaseModel):
    key: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=4, max_length=500)
    admin: bool
    user: bool


class RolePermissionUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=4, max_length=500)
    admin: bool
    user: bool
