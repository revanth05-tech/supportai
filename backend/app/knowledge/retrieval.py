"""Tenant-scoped vector retrieval using PostgreSQL + pgvector."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.models import Chunk


DEFAULT_TOP_K = 5
DEFAULT_SIMILARITY_FLOOR = 0.35


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by vector similarity search."""

    id: UUID
    knowledge_item_id: UUID
    content: str
    similarity: float
    embedding_model: str


async def retrieve_chunks(
    session: AsyncSession,
    query_embedding: list[float],
    *,
    top_k: int = DEFAULT_TOP_K,
    similarity_floor: float = DEFAULT_SIMILARITY_FLOOR,
) -> list[RetrievedChunk]:
    """Retrieve the most similar chunks for the current tenant."""

    if not query_embedding:
        return []

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    if not 0.0 <= similarity_floor <= 1.0:
        raise ValueError("similarity_floor must be between 0 and 1.")

    # pgvector cosine distance.
    cosine_distance = Chunk.embedding.cosine_distance(query_embedding)

    # cosine similarity = 1 - cosine distance
    similarity = (1 - cosine_distance).label("similarity")

    statement = (
        select(
            Chunk.id,
            Chunk.knowledge_item_id,
            Chunk.content,
            Chunk.embedding_model,
            similarity,
        )
        .order_by(cosine_distance)
        .limit(top_k)
    )

    result = await session.execute(statement)

    chunks: list[RetrievedChunk] = []

    for row in result:
        score = float(row.similarity)

        if score < similarity_floor:
            continue

        chunks.append(
            RetrievedChunk(
                id=row.id,
                knowledge_item_id=row.knowledge_item_id,
                content=row.content,
                similarity=score,
                embedding_model=row.embedding_model,
            )
        )

    return chunks