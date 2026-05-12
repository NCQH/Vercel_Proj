import asyncio
import httpx

# Shared async client with connection pooling
_async_client: httpx.AsyncClient | None = None

_TIMEOUT = httpx.Timeout(connect=3.0, read=15.0, write=15.0, pool=3.0)
_LIMITS = httpx.Limits(max_connections=120, max_keepalive_connections=30)


def get_async_client() -> httpx.AsyncClient:
    """Return singleton AsyncClient with tuned limits and timeout."""
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=_TIMEOUT, limits=_LIMITS)
    return _async_client


async def async_request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    json: dict | None = None,
    params: dict | None = None,
    attempts: int = 3,
    backoff_seconds: float = 0.25,
) -> httpx.Response:
    """Make async HTTP request with small retry/backoff for transient failures."""
    client = get_async_client()
    last_exc: Exception | None = None

    for attempt in range(max(1, attempts)):
        try:
            response = await client.request(method, url, headers=headers, json=json, params=params)
            if response.status_code >= 500 and attempt < attempts - 1:
                await asyncio.sleep(backoff_seconds * (2**attempt))
                continue
            return response
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt >= attempts - 1:
                raise
            await asyncio.sleep(backoff_seconds * (2**attempt))

    if last_exc:
        raise last_exc
    raise RuntimeError("async_request_with_retry failed without response")


async def close_async_client() -> None:
    """Close shared AsyncClient on app shutdown."""
    global _async_client
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None
