from __future__ import annotations

import secrets

from fastapi import Cookie, HTTPException, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import Settings, get_settings

ADMIN_COOKIE_NAME = "admin_session"
ADMIN_COOKIE_MAX_AGE_SECONDS = 8 * 60 * 60
_ADMIN_SALT = "python-doc-chat.admin-session.v1"


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    if not settings.session_secret:
        raise RuntimeError(
            "SESSION_SECRET is not configured. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return URLSafeTimedSerializer(settings.session_secret, salt=_ADMIN_SALT)


def verify_password(submitted: str, settings: Settings) -> bool:
    if not settings.admin_password:
        return False
    return secrets.compare_digest(submitted, settings.admin_password)


def issue_cookie(response: Response, settings: Settings) -> None:
    token = _serializer(settings).dumps("admin")
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        max_age=ADMIN_COOKIE_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def clear_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME,
        path="/",
        secure=settings.is_production,
        samesite="lax",
    )


def require_admin(
    admin_session: str | None = Cookie(default=None, alias=ADMIN_COOKIE_NAME),
) -> None:
    settings = get_settings()
    if not admin_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        _serializer(settings).loads(admin_session, max_age=ADMIN_COOKIE_MAX_AGE_SECONDS)
    except SignatureExpired as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired") from e
    except BadSignature as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from e
