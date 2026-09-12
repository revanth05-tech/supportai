"""Validation helpers for knowledge items."""

SUPPORTED_ITEM_TYPES = {
    "Faq",
    "Service",
    "Policy",
    "BusinessProfile",
}


def validate_knowledge_item(
    item_type: str,
    payload: dict,
) -> None:
    """Validate a knowledge item before persistence."""

    if item_type not in SUPPORTED_ITEM_TYPES:
        raise ValueError(
            f"Unsupported knowledge item type: {item_type}"
        )

    if not payload:
        raise ValueError(
            "Knowledge payload cannot be empty."
        )