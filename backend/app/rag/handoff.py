"""Handoff and confidence-gating logic for support conversations."""

from dataclasses import dataclass


REFUSAL_PHRASE = (
    "I don't have that information, but I can connect you with the team."
)

HUMAN_REQUEST_PHRASES = (
    "human",
    "real person",
    "agent",
    "representative",
    "customer support",
    "talk to someone",
    "speak to someone",
)


@dataclass(frozen=True)
class HandoffDecision:
    """Result of evaluating whether a conversation needs human handoff."""

    should_handoff: bool
    reason: str | None = None


def detect_explicit_human_request(message: str) -> bool:
    """Return True when the customer explicitly asks for a human."""

    normalized = message.strip().lower()

    if not normalized:
        return False

    return any(
        phrase in normalized
        for phrase in HUMAN_REQUEST_PHRASES
    )


def should_handoff_for_grounding(
    *,
    top_similarity: float | None,
    similarity_floor: float = 0.35,
) -> bool:
    """Return True when retrieval confidence is insufficient."""

    if top_similarity is None:
        return True

    return top_similarity < similarity_floor


def evaluate_handoff(
    *,
    message: str,
    top_similarity: float | None,
    similarity_floor: float = 0.35,
) -> HandoffDecision:
    """Evaluate the initial handoff gate before LLM generation."""

    if detect_explicit_human_request(message):
        return HandoffDecision(
            should_handoff=True,
            reason="Explicit human request",
        )

    if should_handoff_for_grounding(
        top_similarity=top_similarity,
        similarity_floor=similarity_floor,
    ):
        return HandoffDecision(
            should_handoff=True,
            reason="Insufficient knowledge grounding",
        )

    return HandoffDecision(
        should_handoff=False,
    )