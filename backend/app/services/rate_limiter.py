import time
from dataclasses import dataclass, field


class RedisRateLimiter:
    def __init__(self, redis_client, limit: int, window_seconds: int):
        self.redis = redis_client
        self.limit = limit
        self.window_seconds = window_seconds

    def allow(self, key: str) -> bool:
        now = time.time()
        redis_key = f"rate:{key}"
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, now - self.window_seconds)
        pipe.zcard(redis_key)
        _, count = pipe.execute()
        if int(count) >= self.limit:
            return False
        self.redis.zadd(redis_key, {str(now): now})
        self.redis.expire(redis_key, self.window_seconds)
        return True


@dataclass
class InMemoryRateLimiter:
    limit: int
    window_seconds: int
    buckets: dict[str, list[float]] = field(default_factory=dict)

    def allow(self, key: str, now: float | None = None) -> bool:
        current = time.time() if now is None else now
        bucket = [ts for ts in self.buckets.get(key, []) if ts > current - self.window_seconds]
        if len(bucket) >= self.limit:
            self.buckets[key] = bucket
            return False
        bucket.append(current)
        self.buckets[key] = bucket
        return True
