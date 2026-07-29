import pytest
from datetime import timedelta
from src.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    is_token_valid,
    encrypt_api_key,
    decrypt_api_key,
)

def test_password_hashing():
    password = "supersecretpassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_create_and_decode_access_token():
    subject = "user123"
    extra_claims = {"workspace_id": "ws-001", "workspace_role": "owner"}
    token = create_access_token(subject=subject, extra=extra_claims)
    
    assert token is not None
    assert isinstance(token, str)
    
    payload = decode_token(token)
    assert payload["sub"] == subject
    assert payload["workspace_id"] == "ws-001"
    assert payload["workspace_role"] == "owner"
    assert payload["type"] == "access"
    assert "exp" in payload

def test_create_and_decode_refresh_token():
    subject = "user123"
    token = create_refresh_token(subject)
    
    assert token is not None
    
    payload = decode_token(token)
    assert payload["sub"] == subject
    assert payload["type"] == "refresh"
    assert "exp" in payload

def test_is_token_valid():
    access_token = create_access_token("user1")
    refresh_token = create_refresh_token("user1")
    
    assert is_token_valid(access_token, token_type="access") is not None
    assert is_token_valid(access_token, token_type="refresh") is None
    
    assert is_token_valid(refresh_token, token_type="refresh") is not None
    assert is_token_valid(refresh_token, token_type="access") is None
    
    assert is_token_valid("invalid.token.string") is None

def test_api_key_encryption_decryption():
    original_key = "sk-live-1234567890abcdef"
    
    encrypted_key = encrypt_api_key(original_key)
    assert encrypted_key != original_key
    
    decrypted_key = decrypt_api_key(encrypted_key)
    assert decrypted_key == original_key
