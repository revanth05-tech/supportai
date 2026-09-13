from uuid import uuid4

import pytest

from app.rag.dependencies import get_embedder_model_dir
from app.rag.openai_compatible import OpenAICompatibleClient


def test_embedder_model_directory_points_to_expected_model():
    model_dir = get_embedder_model_dir()

    assert model_dir.endswith(
        "models\\all-MiniLM-L6-v2"
    ) or model_dir.endswith(
        "models/all-MiniLM-L6-v2"
    )


def test_openrouter_default_base_url():
    from app.rag.dependencies import get_tenant_llm_client

    assert get_tenant_llm_client is not None


def test_openai_compatible_client_can_be_constructed():
    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="https://example.com/v1",
        model="test-model",
    )

    assert client.api_key == "test-key"
    assert client.base_url == "https://example.com/v1"
    assert client.model == "test-model"