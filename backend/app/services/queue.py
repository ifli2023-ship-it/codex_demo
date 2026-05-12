import json
import uuid
from datetime import UTC, datetime

from app.core import settings
from app.models.schemas import JobState, Report


QUEUE_KEY = "analysis:queue"


def job_key(job_id: str) -> str:
    return f"job:{job_id}"


def report_key(report_id: str) -> str:
    return f"report:{report_id}"


def cache_key(normalized_repo: str) -> str:
    return f"cache:{normalized_repo.lower()}"


class JobStore:
    def __init__(self, redis_client):
        self.redis = redis_client

    def create_job(self, repo_url: str, normalized_repo: str) -> JobState:
        job = JobState(
            id=str(uuid.uuid4()),
            repo_url=repo_url,
            normalized_repo=normalized_repo,
            status="queued",
            step="Queued",
            progress=0,
        )
        self.redis.setex(job_key(job.id), settings.report_ttl_seconds, job.model_dump_json())
        self.redis.lpush(QUEUE_KEY, job.id)
        return job

    def get_job(self, job_id: str) -> JobState | None:
        raw = self.redis.get(job_key(job_id))
        return JobState.model_validate_json(raw) if raw else None

    def update_job(self, job_id: str, **updates) -> JobState:
        job = self.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        data = job.model_dump()
        data.update(updates)
        updated = JobState(**data)
        self.redis.setex(job_key(job_id), settings.report_ttl_seconds, updated.model_dump_json())
        return updated

    def get_cached_job(self, normalized_repo: str) -> str | None:
        return self.redis.get(cache_key(normalized_repo))

    def set_cached_job(self, normalized_repo: str, job_id: str) -> None:
        self.redis.setex(cache_key(normalized_repo), settings.cache_ttl_seconds, job_id)

    def save_report(self, report: Report) -> None:
        self.redis.setex(report_key(report.id), settings.report_ttl_seconds, report.model_dump_json())

    def get_report(self, report_id: str) -> Report | None:
        raw = self.redis.get(report_key(report_id))
        return Report.model_validate_json(raw) if raw else None


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
