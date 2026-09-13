from app.rag.handoff import (
    evaluate_handoff,
    detect_explicit_human_request,
    should_handoff_for_grounding,
)


def test_detects_explicit_human_request():
    assert detect_explicit_human_request(
        "I want to talk to a human"
    )


def test_detects_real_person_request():
    assert detect_explicit_human_request(
        "Can I speak to a real person?"
    )


def test_does_not_trigger_for_normal_question():
    assert not detect_explicit_human_request(
        "What are your business hours?"
    )


def test_missing_similarity_requires_handoff():
    assert should_handoff_for_grounding(
        top_similarity=None
    )


def test_low_similarity_requires_handoff():
    assert should_handoff_for_grounding(
        top_similarity=0.20,
        similarity_floor=0.35,
    )


def test_good_similarity_does_not_require_handoff():
    assert not should_handoff_for_grounding(
        top_similarity=0.80,
        similarity_floor=0.35,
    )


def test_explicit_human_request_wins():
    decision = evaluate_handoff(
        message="I want a human agent",
        top_similarity=0.95,
    )

    assert decision.should_handoff
    assert decision.reason == "Explicit human request"


def test_low_grounding_triggers_handoff():
    decision = evaluate_handoff(
        message="What is your refund policy?",
        top_similarity=0.20,
    )

    assert decision.should_handoff
    assert decision.reason == "Insufficient knowledge grounding"


def test_good_grounding_allows_rag():
    decision = evaluate_handoff(
        message="What is your refund policy?",
        top_similarity=0.80,
    )

    assert not decision.should_handoff
    assert decision.reason is None