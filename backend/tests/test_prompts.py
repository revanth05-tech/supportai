from app.rag.prompts import (
    REFUSAL_PHRASE,
    RetrievedContext,
    build_system_prompt,
)


def test_prompt_contains_business_and_agent_context():
    prompt = build_system_prompt(
        business_name="Acme Support",
        agent_name="Ava",
        tone="friendly",
        instructions="Keep answers short.",
        retrieved_chunks=[],
    )

    assert "Acme Support" in prompt
    assert "Ava" in prompt
    assert "friendly" in prompt
    assert "Keep answers short." in prompt


def test_prompt_contains_retrieved_knowledge():
    prompt = build_system_prompt(
        business_name="Acme Support",
        agent_name="Ava",
        tone="professional",
        instructions="",
        retrieved_chunks=[
            RetrievedContext(
                content="Our refund window is 30 days.",
                similarity=0.91,
            )
        ],
    )

    assert "Our refund window is 30 days." in prompt
    assert "0.9100" in prompt


def test_prompt_contains_grounding_and_refusal_rules():
    prompt = build_system_prompt(
        business_name="Acme Support",
        agent_name="Ava",
        tone="professional",
        instructions="",
        retrieved_chunks=[],
    )

    assert "Do not invent" in prompt
    assert REFUSAL_PHRASE in prompt


def test_prompt_handles_empty_retrieval():
    prompt = build_system_prompt(
        business_name="Acme Support",
        agent_name="Ava",
        tone="professional",
        instructions="",
        retrieved_chunks=[],
    )

    assert "No relevant knowledge was retrieved." in prompt