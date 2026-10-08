"""Public request and response schemas for the identity API."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = Field(
        default=None,
        max_length=200,
        alias="displayName",
    )
    tenant_name: str = Field(min_length=1, max_length=200, alias="tenantName")

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
    model_config = ConfigDict(serialize_by_alias=True)

    access_token: str = Field(serialization_alias="accessToken")
    token_type: str = Field(
        default="bearer",
        serialization_alias="tokenType",
    )
    expires_in: int = Field(serialization_alias="expiresIn")

class CurrentUserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str | None = Field(serialization_alias="displayName")
    tenant_id: UUID = Field(serialization_alias="tenantId")
    tenant_name: str = Field(serialization_alias="tenantName")
    site_key: str = Field(serialization_alias="siteKey")
