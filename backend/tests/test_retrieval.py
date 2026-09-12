import pytest

from app.knowledge.retrieval import (
    DEFAULT_SIMILARITY_FLOOR,
    DEFAULT_TOP_K,
    retrieve_chunks,
)


def test_retrieval_defaults():
    assert DEFAULT_TOP_K == 5
    assert DEFAULT_SIMILARITY_FLOOR == 0.35


@pytest.mark.anyio
async def test_empty_embedding_returns_no_results():
    result = await retrieve_chunks(
        session=None,
        query_embedding=[],
    )

    assert result == []


@pytest.mark.anyio
async def test_invalid_top_k_is_rejected():
    with pytest.raises(ValueError, match="top_k"):
        await retrieve_chunks(
            session=None,
            query_embedding=[0.1],
            top_k=0,
        )


@pytest.mark.anyio
async def test_invalid_similarity_floor_is_rejected():
    with pytest.raises(ValueError, match="similarity_floor"):
        await retrieve_chunks(
            session=None,
            query_embedding=[0.1],
            similarity_floor=1.5,
        )