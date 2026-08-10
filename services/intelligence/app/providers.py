from __future__ import annotations

from dataclasses import asdict, dataclass


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
