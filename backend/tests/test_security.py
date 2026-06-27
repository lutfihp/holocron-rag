import uuid

import pytest

from app.core.security import (
    InvalidTokenError,
    decode_session_token,
    encode_session_token,
    hash_password,
    verify_password,
)


def test_hash_password_returns_different_hashes_for_same_input():
    h1 = hash_password("correct horse battery staple")
    h2 = hash_password("correct horse battery staple")
    assert h1 != h2  # bcrypt salts


def test_verify_password_correct():
    h = hash_password("secret-123")
    assert verify_password("secret-123", h) is True


def test_verify_password_wrong():
    h = hash_password("secret-123")
    assert verify_password("secret-456", h) is False


def test_verify_password_with_malformed_hash_returns_false():
    assert verify_password("x", "not-a-bcrypt-hash") is False


def test_encode_decode_roundtrip():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = encode_session_token(user_id=user_id, tenant_id=tenant_id, ttl_seconds=60)
    claims = decode_session_token(token)
    assert claims.user_id == user_id
    assert claims.tenant_id == tenant_id


def test_expired_token_rejected():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = encode_session_token(user_id=user_id, tenant_id=tenant_id, ttl_seconds=-1)
    with pytest.raises(InvalidTokenError):
        decode_session_token(token)


def test_tampered_token_rejected():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    token = encode_session_token(user_id=user_id, tenant_id=tenant_id, ttl_seconds=60)
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises(InvalidTokenError):
        decode_session_token(tampered)
