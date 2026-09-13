"""RAG orchestration service."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.embedder import Embedder
from app.knowledge.retrieval import retrieve_chunks
from app.rag.handoff import evaluate_handoff
from app.rag.llm import LLMClient
from app.rag.prompts import RetrievedContext, build_system_prompt


class RagService:
    """Coordinate retrieval, grounding, handoff, prompting, and generation."""

    def __init__(
        self,
        *,
        embedder: Embedder,
        llm_client: LLMClient,
        similarity_floor: float = 0.35,
        top_k: int = 5,
    ) -> None:
        self.embedder = embedder
        self.llm_client = llm_client
        self.similarity_floor = similarity_floor
        self.top_k = top_k

    async def stream_response(
        self,
        *,
        session: AsyncSession,
        message: str,
        business_name: str,
        agent_name: str,
        tone: str,
        instructions: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[tuple[str, dict]]:
        """Generate a grounded response or request human handoff."""

        # 1. Embed the user's question.
        query_embedding = await self.embedder.embed(message)

        # 2. Retrieve tenant-scoped knowledge.
        chunks = await retrieve_chunks(
            session,
            query_embedding,
            top_k=self.top_k,
            similarity_floor=self.similarity_floor,
        )

        top_similarity = chunks[0].similarity if chunks else None

        # 3. Evaluate whether the conversation should be handed off.
        decision = evaluate_handoff(
            message=message,
            top_similarity=top_similarity,
            similarity_floor=self.similarity_floor,
        )

        if decision.should_handoff:
            yield "handoff", {
                "reason": decision.reason,
            }
            return

        # 4. Convert retrieved database chunks into prompt context.
        retrieved_context = [
            RetrievedContext(
                content=chunk.content,
                similarity=chunk.similarity,
            )
            for chunk in chunks
        ]

        # 5. Build the grounded system prompt.
        system_prompt = build_system_prompt(
            business_name=business_name,
            agent_name=agent_name,
            tone=tone,
            instructions=instructions,
            retrieved_chunks=retrieved_context,
        )

        # 6. Ask the LLM for a streamed answer.
        async for token in self.llm_client.stream_chat(
            system_prompt=system_prompt,
            user_message=message,
            history=history,
        ):
            yield "token", {
                "content": token,
            }

        # 7. Tell the caller generation completed.
        yield "done", {}