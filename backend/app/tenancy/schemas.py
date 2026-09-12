"""Tenant and agent configuration API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentConfig(BaseModel):
    """Public agent configuration stored inside the tenant."""

    model_config = ConfigDict(extra="forbid")

    business_name: str = Field(default="", max_length=200)
    tone: str = Field(default="friendly", max_length=100)
    instructions: str = Field(default="", max_length=4000)
    welcome_message: str = Field(
        default="Hi! How can I help you today?",
        max_length=500,
    )


class AgentConfigResponse(BaseModel):
    """Agent configuration returned to the dashboard."""

    tenant_id: UUID
    business_name: str
    tone: str
    instructions: str
    welcome_message: str
    allowed_origins: list[str]


class AgentConfigUpdate(BaseModel):
    """Dashboard request for updating agent configuration."""

    model_config = ConfigDict(extra="forbid")

    business_name: str = Field(default="", max_length=200)
    tone: str = Field(default="friendly", max_length=100)
    instructions: str = Field(default="", max_length=4000)
    welcome_message: str = Field(
        default="Hi! How can I help you today?",
        max_length=500,
    )
    allowed_origins: list[str] = Field(default_factory=list, max_length=20)


class SiteKeyResponse(BaseModel):
    """Response returned after site-key rotation."""

    site_key: str
class LlmCredentialResponse(BaseModel):
    """LLM credential metadata returned without exposing the API key."""

    provider: str
    base_url: str | None
    configured: bool


class LlmCredentialUpdate(BaseModel):
    """Request for configuring a tenant's LLM provider."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=50)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str = Field(min_length=1, max_length=1000)