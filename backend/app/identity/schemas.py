"""Public request and response schemas for the identity API."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = Field(default=None, max_length=200)
    tenant_name: str = Field(min_length=1, max_length=200)

    @field_validator("tenant_name")
    @classmethod
    def strip_tenant_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tenant name is required.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None
    tenant_id: UUID
    tenant_name: str
