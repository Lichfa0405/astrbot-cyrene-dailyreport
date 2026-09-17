# http_client.py
import httpx
from httpx import ConnectError, HTTPStatusError, Response, TimeoutException
import tenacity
from tenacity import retry, stop_after_attempt, wait_fixed
from astrbot.api import logger


class AsyncHttpx:
    @classmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=(
            tenacity.retry_if_exception_type(
                (TimeoutException, ConnectError, HTTPStatusError)
            )
        ),
    )
    async def get(
        cls,
        url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> Response:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response
            except (TimeoutException, ConnectError, HTTPStatusError) as e:
                logger.error(f"Request to {url} failed due to: {e}")
                raise

    @classmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=(
            tenacity.retry_if_exception_type(
                (TimeoutException, ConnectError, HTTPStatusError)
            )
        ),
    )
    async def post(
        cls, url: str, data: dict[str, str], headers: dict[str, str]
    ) -> Response:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, data=data, headers=headers)
                response.raise_for_status()
                return response
            except (TimeoutException, ConnectError, HTTPStatusError) as e:
                logger.error(f"Request to {url} failed due to: {e}")
                raise


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}