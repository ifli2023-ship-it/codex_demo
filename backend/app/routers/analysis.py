from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core import settings
from app.models.schemas import AnalyzeRequest, AnalyzeResponse, JobState
from app.services.queue import JobStore
from app.services.rate_limiter import RedisRateLimiter
from app.services.redis_client import get_redis
from app.utils.github import normalize_github_url


router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_store() -> JobStore:
    return JobStore(get_redis())


@router.post("", response_model=AnalyzeResponse, status_code=status.HTTP_202_ACCEPTED)
def create_analysis(payload: AnalyzeRequest, request: Request, store: JobStore = Depends(get_store)) -> AnalyzeResponse:
    limiter = RedisRateLimiter(get_redis(), settings.rate_limit_count, settings.rate_limit_window_seconds)
    if not limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    try:
        normalized, _ = normalize_github_url(payload.repo_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cached_job_id = store.get_cached_job(normalized)
    if cached_job_id:
        cached_job = store.get_job(cached_job_id)
        if cached_job and cached_job.status == "completed":
            return AnalyzeResponse(
                job_id=cached_job.id,
                report_url=f"/reports/{cached_job.report_id}",
                cached=True,
            )

    job = store.create_job(payload.repo_url, normalized)
    return AnalyzeResponse(job_id=job.id, cached=False)


@router.get("/{job_id}", response_model=JobState)
def get_analysis(job_id: str, store: JobStore = Depends(get_store)) -> JobState:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found or expired.")
    return job
