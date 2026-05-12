from app.services.rate_limiter import InMemoryRateLimiter


def test_rate_limiter_allows_under_limit():
    limiter = InMemoryRateLimiter(limit=3, window_seconds=60)
    assert limiter.allow("1.2.3.4", now=1)
    assert limiter.allow("1.2.3.4", now=2)
    assert limiter.allow("1.2.3.4", now=3)


def test_rate_limiter_blocks_at_limit():
    limiter = InMemoryRateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("ip", now=1)
    assert limiter.allow("ip", now=2)
    assert not limiter.allow("ip", now=3)


def test_rate_limiter_window_expires_old_entries():
    limiter = InMemoryRateLimiter(limit=1, window_seconds=10)
    assert limiter.allow("ip", now=1)
    assert not limiter.allow("ip", now=5)
    assert limiter.allow("ip", now=12)
