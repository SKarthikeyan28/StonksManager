# jwt.py - handles creation and decoding of JWT access tokens

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.config import settings

# HTTPBearer extracts the token from the Authorization: Bearer <token> header
bearer_scheme = HTTPBearer()


def create_access_token(user_id: str) -> str:
    # sub (subject) = who the token belongs to (user UUID)
    # iat (issued at) = when the token was created
    # exp (expiry) = when the token stops being valid (auto-checked on decode)
    payload = {
        "sub": user_id,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> str:
    # FastAPI dependency — add to any protected route with: Depends(get_current_user_id)
    # Automatically returns 401 if token is missing, expired, or invalid
    return decode_access_token(credentials.credentials)