"""Test embedding implementation."""

import hashlib

from app.knowledge.embedder import Embedder


class TestEmbedder(Embedder):
    """Small deterministic embedder used by tests."""

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()

        values = [
            (byte / 255.0) * 2.0 - 1.0
            for byte in digest
        ]

        return (values * ((self.dimension + len(values) - 1) // len(values)))[: self.dimension]