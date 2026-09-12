"""Knowledge base CRUD and embedding ingestion services."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.chunker import chunk_knowledge
from app.knowledge.models import Chunk, KnowledgeItem, KnowledgeItemType
from app.knowledge.onnx_embedder import OnnxEmbedder
from app.knowledge.schemas import KnowledgeItemCreate, KnowledgeItemUpdate
from app.knowledge.validators import validate_knowledge_item


def _model_dir() -> str:
    """Return the local all-MiniLM-L6-v2 model directory."""
    from pathlib import Path

    return str(
        Path(__file__).resolve().parents[2]
        / "models"
        / "all-MiniLM-L6-v2"
    )


def _get_embedder() -> OnnxEmbedder:
    """Create the local ONNX embedder."""
    return OnnxEmbedder(_model_dir())


async def list_knowledge(
    session: AsyncSession,
) -> list[KnowledgeItem]:
    """List knowledge items for the current tenant."""
    result = await session.scalars(
        select(KnowledgeItem).order_by(KnowledgeItem.created_at.desc())
    )

    return list(result.all())


async def get_knowledge(
    session: AsyncSession,
    item_id: UUID,
) -> KnowledgeItem | None:
    """Get one knowledge item."""
    return await session.scalar(
        select(KnowledgeItem).where(KnowledgeItem.id == item_id)
    )


async def _replace_chunks(
    session: AsyncSession,
    item: KnowledgeItem,
) -> None:
    """Rebuild all chunks and embeddings for a knowledge item."""

    existing_chunks = await session.scalars(
        select(Chunk).where(Chunk.knowledge_item_id == item.id)
    )

    for chunk in existing_chunks.all():
        await session.delete(chunk)

    texts = chunk_knowledge(
        item.item_type.value,
        item.payload,
    )

    if not texts:
        return

    embedder = _get_embedder()

    embeddings = await embedder.embed_many(texts)

    for ordinal, (content, embedding) in enumerate(
        zip(texts, embeddings)
    ):
        session.add(
            Chunk(
                tenant_id=item.tenant_id,
                knowledge_item_id=item.id,
                ordinal=ordinal,
                content=content,
                embedding=embedding,
                embedding_model=embedder.model_name,
            )
        )


async def create_knowledge(
    session: AsyncSession,
    payload: KnowledgeItemCreate,
) -> KnowledgeItem:
    """Create a knowledge item and generate its vector chunks."""

    validate_knowledge_item(
        payload.item_type,
        payload.payload,
    )

    try:
        item_type = KnowledgeItemType(payload.item_type)
    except ValueError as exc:
        raise ValueError("Unsupported knowledge item type.") from exc

    item = KnowledgeItem(
        item_type=item_type,
        payload=payload.payload,
    )

    session.add(item)

    await session.flush()

    await _replace_chunks(session, item)

    await session.commit()
    await session.refresh(item)

    return item


async def update_knowledge(
    session: AsyncSession,
    item: KnowledgeItem,
    payload: KnowledgeItemUpdate,
) -> KnowledgeItem:
    """Update a knowledge item and rebuild its vector chunks."""

    validate_knowledge_item(
        payload.item_type,
        payload.payload,
    )

    try:
        item_type = KnowledgeItemType(payload.item_type)
    except ValueError as exc:
        raise ValueError("Unsupported knowledge item type.") from exc

    item.item_type = item_type
    item.payload = payload.payload

    await _replace_chunks(session, item)

    await session.commit()
    await session.refresh(item)

    return item


async def delete_knowledge(
    session: AsyncSession,
    item: KnowledgeItem,
) -> None:
    """Delete a knowledge item and its chunks."""

    await session.delete(item)
    await session.commit()