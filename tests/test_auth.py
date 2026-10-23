import uuid

from src.auth import service as auth_service
from src.auth.constants import TokenType


def test_password_hashing() -> None:
    raw_pass = "SecurePass123!"
    hashed = auth_service.hash_password(raw_pass)
    assert hashed != raw_pass
    assert auth_service.verify_password(raw_pass, hashed)
    assert not auth_service.verify_password("WrongPassword", hashed)


def test_jwt_token_flow() -> None:
    user_id = uuid.uuid4()
    email = "test@example.com"

    tokens = auth_service.create_auth_tokens(user_id, email)
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None

    access_payload = auth_service.decode_token(tokens.access_token, expected_type=TokenType.ACCESS)
    assert access_payload.sub == str(user_id)
    assert access_payload.email == email
    assert access_payload.token_type == TokenType.ACCESS

    refresh_payload = auth_service.decode_token(
        tokens.refresh_token, expected_type=TokenType.REFRESH
    )
    assert refresh_payload.sub == str(user_id)
    assert refresh_payload.token_type == TokenType.REFRESH
