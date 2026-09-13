from app.common.opaque_tokens import (
    generate_opaque_token,
    hash_opaque_token,
)


def test_generate_opaque_token_is_random():
    token_one = generate_opaque_token()
    token_two = generate_opaque_token()

    assert token_one != token_two
    assert len(token_one) > 20


def test_hash_is_deterministic():
    token = "test-session-token"

    assert hash_opaque_token(token) == hash_opaque_token(token)


def test_hash_does_not_equal_raw_token():
    token = generate_opaque_token()

    assert hash_opaque_token(token) != token