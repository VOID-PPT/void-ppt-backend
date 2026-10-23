import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from src.auth.config import auth_settings
from src.auth.constants import TokenType
from src.auth.exceptions import InvalidToken, TokenExpired
from src.auth.schemas import TokenPayload, TokenResponse

password_hash = PasswordHash((Argon2Hasher(),))

# Auth Service

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def create_token(
    user_id: uuid.UUID,
    email: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    expire = now + expires_delta
    payload = {
        "sub": str(user_id),
        "email": email,
        "token_type": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, auth_settings.JWT_SECRET, algorithm=auth_settings.JWT_ALG)


def create_auth_tokens(user_id: uuid.UUID, email: str) -> TokenResponse:
    access_token = create_token(
        user_id=user_id,
        email=email,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_token(
        user_id=user_id,
        email=email,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def decode_token(token: str, expected_type: TokenType | None = None) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            auth_settings.JWT_SECRET,
            algorithms=[auth_settings.JWT_ALG],
        )
        token_data = TokenPayload(**payload)
        if expected_type and token_data.token_type != expected_type:
            raise InvalidToken(detail=f"Expected {expected_type.value} token")
        return token_data
    except jwt.ExpiredSignatureError as err:
        raise TokenExpired() from err
    except (jwt.PyJWTError, ValueError) as err:
        raise InvalidToken() from err
