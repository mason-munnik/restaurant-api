import secrets

from fastapi import Header, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core import config


def require_api_key(
    x_api_key: str | None = Header(default=None, alias=config.API_KEY_HEADER),
) -> None:
    expected = config.api_key()

    # Checked FIRST, deliberately: if the header were compared first, an unset
    # API_KEY plus a missing header reduces to compare_digest("", "") -> True
    # and the endpoint would fail OPEN.
    if not expected:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Server API key not configured"
        )
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing API key")
    # Compare bytes: compare_digest raises TypeError on non-ASCII str, which
    # would surface as an unhandled 500 instead of a clean 403.
    if not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid API key")


# In-memory fixed-window counters keyed by client IP. Per-process only: fine for
# one uvicorn worker; a multi-worker deploy needs storage_uri="redis://...".
limiter = Limiter(
    key_func=get_remote_address, storage_uri="memory://", headers_enabled=True
)
