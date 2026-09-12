from pathlib import Path

import pytest

from app.knowledge.onnx_embedder import OnnxEmbedder


MODEL_DIR = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "all-MiniLM-L6-v2"
)


@pytest.mark.anyio
async def test_onnx_embedder_returns_384_dimensions():
    embedder = OnnxEmbedder(MODEL_DIR)

    embedding = await embedder.embed(
        "How can I reset my password?"
    )

    assert len(embedding) == 384


@pytest.mark.anyio
async def test_onnx_embedding_is_normalized():
    embedder = OnnxEmbedder(MODEL_DIR)

    embedding = await embedder.embed(
        "How can I reset my password?"
    )

    norm = sum(value * value for value in embedding) ** 0.5

    assert norm == pytest.approx(1.0, abs=1e-5)


@pytest.mark.anyio
async def test_similar_texts_have_higher_similarity():
    embedder = OnnxEmbedder(MODEL_DIR)

    first = await embedder.embed(
        "How do I reset my password?"
    )

    similar = await embedder.embed(
        "I forgot my password. How can I change it?"
    )

    unrelated = await embedder.embed(
        "Our office is closed on Sunday."
    )

    similar_score = sum(
        a * b for a, b in zip(first, similar)
    )

    unrelated_score = sum(
        a * b for a, b in zip(first, unrelated)
    )

    assert similar_score > unrelated_score