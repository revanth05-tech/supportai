from app.knowledge.chunker import (
    MAX_POLICY_CHUNK_SIZE,
    chunk_knowledge,
)


def test_faq_becomes_one_chunk() -> None:
    chunks = chunk_knowledge(
        "Faq",
        {
            "question": "What are your hours?",
            "answer": "We are open from 9 AM to 6 PM.",
        },
    )

    assert len(chunks) == 1
    assert "What are your hours?" in chunks[0]
    assert "9 AM to 6 PM" in chunks[0]


def test_service_becomes_one_chunk() -> None:
    chunks = chunk_knowledge(
        "Service",
        {
            "name": "Cloud Migration",
            "description": "We migrate applications to the cloud.",
        },
    )

    assert len(chunks) == 1
    assert "Cloud Migration" in chunks[0]


def test_business_profile_creates_atomic_chunks() -> None:
    chunks = chunk_knowledge(
        "BusinessProfile",
        {
            "business_name": "SupportAI",
            "location": "Hyderabad",
            "description": "AI customer support.",
        },
    )

    assert len(chunks) == 3


def test_large_policy_is_split_into_1200_character_chunks() -> None:
    content = "A" * 2500

    chunks = chunk_knowledge(
        "Policy",
        {"content": content},
    )

    assert len(chunks) == 3
    assert all(len(chunk) <= MAX_POLICY_CHUNK_SIZE for chunk in chunks)
    assert "".join(chunks) == content


def test_empty_policy_returns_no_chunks() -> None:
    assert chunk_knowledge(
        "Policy",
        {"content": ""},
    ) == []