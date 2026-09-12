"""Knowledge item chunking."""

from typing import Any


MAX_POLICY_CHUNK_SIZE = 1200


def _string_value(payload: dict[str, Any], *keys: str) -> str:
    """Return the first non-empty string value for the given keys."""

    for key in keys:
        value = payload.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def chunk_knowledge(
    item_type: str,
    payload: dict[str, Any],
) -> list[str]:
    """Convert a typed knowledge item into searchable text chunks."""

    if item_type == "Faq":
        question = _string_value(payload, "question")
        answer = _string_value(payload, "answer")

        if question and answer:
            return [f"Question: {question}\nAnswer: {answer}"]

        return [question or answer]

    if item_type == "Service":
        name = _string_value(payload, "name", "title")
        description = _string_value(payload, "description", "content")

        if name and description:
            return [f"Service: {name}\nDescription: {description}"]

        return [name or description]

    if item_type == "BusinessProfile":
        chunks: list[str] = []

        for key, value in payload.items():
            if isinstance(value, str) and value.strip():
                chunks.append(f"{key.replace('_', ' ').title()}: {value.strip()}")

        return chunks

    if item_type == "Policy":
        content = _string_value(payload, "content", "text", "description")

        if not content:
            return []

        return [
            content[i : i + MAX_POLICY_CHUNK_SIZE]
            for i in range(0, len(content), MAX_POLICY_CHUNK_SIZE)
        ]

    return []