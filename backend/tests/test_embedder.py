import pytest

from app.knowledge.embedder import Embedder
from app.knowledge.test_embedder import TestEmbedder


@pytest.mark.anyio
async def test_embedder_has_expected_dimension() -> None:
    embedder = TestEmbedder()

    vector = await embedder.embed("hello world")

    assert len(vector) == 384


@pytest.mark.anyio
async def test_embed_many_returns_one_vector_per_text() -> None:
    embedder = TestEmbedder()

    vectors = await embedder.embed_many(
        ["hello", "world", "support"],
    )

    assert len(vectors) == 3
    assert all(len(vector) == 384 for vector in vectors)


@pytest.mark.anyio
async def test_embedder_is_deterministic() -> None:
    embedder = TestEmbedder()

    first = await embedder.embed("hello")
    second = await embedder.embed("hello")

    assert first == second


def test_embedder_is_abstract() -> None:
    assert Embedder.__abstractmethods__ == {"embed"}