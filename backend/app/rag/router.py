"""RAG API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_tenant, get_db
from app.rag.dependencies import get_rag_service
from app.rag.schemas import RagChatRequest
from app.rag.service import RagService
from fastapi.responses import StreamingResponse

from app.core.sse import stream_sse_events

router = APIRouter(
    prefix="/api/rag",
    tags=["rag"],
)

@router.post("/chat")
async def chat(
    payload: RagChatRequest,
    session: AsyncSession = Depends(get_db),
    tenant=Depends(get_current_tenant),
    rag_service: RagService = Depends(get_rag_service),
):
    """Run a RAG chat turn and stream the response as SSE."""

    agent_config = tenant.agent_config or {}

    business_name = agent_config.get(
        "business_name",
        tenant.name,
    )

    agent_name = agent_config.get(
        "agent_name",
        "AI Support Agent",
    )

    tone = agent_config.get(
        "tone",
        "professional",
    )

    instructions = agent_config.get(
        "instructions",
        "",
    )

    history = [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in payload.history
    ]

    events = rag_service.stream_response(
        session=session,
        message=payload.message,
        business_name=business_name,
        agent_name=agent_name,
        tone=tone,
        instructions=instructions,
        history=history,
    )

    return StreamingResponse(
        stream_sse_events(events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )