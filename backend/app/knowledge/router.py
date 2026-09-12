"""Knowledge base API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_tenant, get_db
from app.knowledge.schemas import (
    KnowledgeItemCreate,
    KnowledgeItemResponse,
    KnowledgeItemUpdate,
)
from app.knowledge.service import (
    create_knowledge,
    delete_knowledge,
    get_knowledge,
    list_knowledge,
    update_knowledge,
)
from app.tenancy.models import Tenant


router = APIRouter(
    prefix="/api/knowledge",
    tags=["Knowledge"],
)


def _to_response(item) -> KnowledgeItemResponse:
    return KnowledgeItemResponse(
        id=item.id,
        item_type=item.item_type.value,
        payload=item.payload,
    )


@router.get(
    "",
    response_model=list[KnowledgeItemResponse],
)
async def get_knowledge_items(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> list[KnowledgeItemResponse]:
    items = await list_knowledge(session)

    return [_to_response(item) for item in items]


@router.get(
    "/{item_id}",
    response_model=KnowledgeItemResponse,
)
async def get_knowledge_item(
    item_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeItemResponse:
    item = await get_knowledge(session, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found.",
        )

    return _to_response(item)


@router.post(
    "",
    response_model=KnowledgeItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_item(
    payload: KnowledgeItemCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeItemResponse:
    try:
        item = await create_knowledge(session, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _to_response(item)


@router.put(
    "/{item_id}",
    response_model=KnowledgeItemResponse,
)
async def update_knowledge_item(
    item_id: UUID,
    payload: KnowledgeItemUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeItemResponse:
    item = await get_knowledge(session, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found.",
        )

    try:
        item = await update_knowledge(session, item, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _to_response(item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_knowledge_item(
    item_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> None:
    item = await get_knowledge(session, item_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge item not found.",
        )

    await delete_knowledge(session, item)