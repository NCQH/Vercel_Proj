import hmac
import os

from fastapi import Header, HTTPException


_INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET", "").strip()
_ENVIRONMENT = (
    os.getenv("ENVIRONMENT")
    or os.getenv("APP_ENV")
    or os.getenv("NODE_ENV")
    or "development"
).strip().lower()
_ALLOW_MISSING_INTERNAL_SECRET = os.getenv("ALLOW_MISSING_INTERNAL_SECRET", "").strip().lower() in {
    "1",
    "true",
    "yes",
}
_PRODUCTION_ENVS = {"production", "prod", "staging"}


def _is_internal_auth_enabled() -> bool:
    return bool(_INTERNAL_API_SECRET)


def _requires_internal_secret() -> bool:
    return _ENVIRONMENT in _PRODUCTION_ENVS and not _ALLOW_MISSING_INTERNAL_SECRET


def verify_internal_request(x_internal_api_secret: str = Header(default="")) -> None:
    """Require shared secret for browser-proxied FastAPI routes.

    Local development remains permissive until INTERNAL_API_SECRET is set.
    Production/staging fail closed unless ALLOW_MISSING_INTERNAL_SECRET=true.
    """
    if not _is_internal_auth_enabled():
        if _requires_internal_secret():
            raise HTTPException(
                status_code=500,
                detail="INTERNAL_API_SECRET is required in production",
            )
        return

    provided = (x_internal_api_secret or "").strip()
    if not hmac.compare_digest(provided, _INTERNAL_API_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")
