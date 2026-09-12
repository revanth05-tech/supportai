"""Embedding interface."""

from abc import ABC, abstractmethod


class Embedder(ABC):
    """Interface for generating normalized text embeddings."""

    dimension: int = 384
    model_name: str = "all-MiniLM-L6-v2"

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding for one text."""

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""

        return [await self.embed(text) for text in texts]