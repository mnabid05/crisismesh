from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    source: str
    code: str
    message: str
    retryable: bool


def provider_failure(source: str, error: Exception) -> dict[str, str | bool]:
    retryable = isinstance(error, (OSError, TimeoutError))
    failure = ProviderFailure(
        source=source,
        code="upstream_unavailable" if retryable else "invalid_provider_response",
        message=str(error),
        retryable=retryable,
    )
    return asdict(failure)


def fetch_provider_json(
    url: str,
    *,
    source: str,
    timeout: float,
    attempts: int = 2,
) -> dict[str, Any]:
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "CrisisMesh/0.4 disaster-intelligence portfolio",
                },
            )
            with urlopen(request, timeout=timeout) as response:  # noqa: S310
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise ValueError(f"{source} returned a non-object response")
            return payload
        except (OSError, TimeoutError) as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(0.15 * (2**attempt))
    raise OSError(f"{source} failed after {attempts} attempts: {error}")
