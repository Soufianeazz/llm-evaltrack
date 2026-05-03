import os

from fastapi import Header, HTTPException, Query


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def resolve_admin_token(
    x_admin_token: str | None,
    authorization: str | None,
    token: str | None,
) -> str | None:
    return x_admin_token or extract_bearer_token(authorization) or token


def verify_admin_token(candidate: str | None) -> None:
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if candidate != admin_token:
        raise HTTPException(status_code=403, detail="Forbidden")


async def require_admin_token(
    x_admin_token: str | None = Header(None),
    authorization: str | None = Header(None),
    token: str | None = Query(None),
) -> None:
    verify_admin_token(resolve_admin_token(x_admin_token, authorization, token))
