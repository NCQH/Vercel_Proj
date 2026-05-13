import hmac
import os

from fastapi import Header, HTTPException


_INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET", "").strip()


def _is_internal_auth_enabled() -> bool:
    return bool(_INTERNAL_API_SECRET)


def verify_internal_request(x_internal_api_secret: str = Header(default="")) -> None:
    """Require shared secret for browser-proxied FastAPI routes when configured.

    Local development remains permissive until INTERNAL_API_SECRET is set.
    Production should set same value in Next.js and FastAPI environments.
    """
    if not _is_internal_auth_enabled():
        return

    provided = (x_internal_api_secret or "").strip()
    if not hmac.compare_digest(provided, _INTERNAL_API_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")
