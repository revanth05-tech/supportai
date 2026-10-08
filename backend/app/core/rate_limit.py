"""Simple in-memory rate limiting for public API requests."""

from collections import defaultdict
from time import monotonic


class RateLimiter:
    """Fixed-window in-memory rate limiter."""

    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        """
        Return True when the request is within the configured limit.

        Requests are tracked independently for each key.
        """

        now = monotonic()
        window_start = now - self.window_seconds

        timestamps = self._requests[key]

        # Remove requests outside the current window.
        self._requests[key] = [
            timestamp
            for timestamp in timestamps
            if timestamp > window_start
        ]

        if len(self._requests[key]) >= self.limit:
            return False

        self._requests[key].append(now)
        return True

    def reset(self, key: str | None = None) -> None:
        """Reset one key or all tracked keys."""

        if key is None:
            self._requests.clear()
            return

        self._requests.pop(key, None)


widget_rate_limiter = RateLimiter(
    limit=20,
    window_seconds=60,
)