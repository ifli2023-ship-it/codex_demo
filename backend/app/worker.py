import logging
import time

from app.services.analyzer import analyze_repository
from app.services.queue import QUEUE_KEY, JobStore
from app.services.redis_client import get_redis
from app.utils.github import normalize_github_url


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("repo-health-worker")


def run_worker() -> None:
    redis = get_redis()
    store = JobStore(redis)
    logger.info("worker started")
    while True:
        item = redis.brpop(QUEUE_KEY, timeout=5)
        if not item:
            continue
        _, job_id = item
        job = store.get_job(job_id)
        if not job:
            continue
        try:
            normalized, clone_url = normalize_github_url(job.repo_url)
            analyze_repository(store, job.id, job.repo_url, normalized, clone_url)
        except Exception as exc:
            logger.exception("analysis failed for %s", job_id)
            try:
                store.update_job(
                    job_id,
                    status="failed",
                    step="Failed",
                    progress=100,
                    error=str(exc),
                )
            except Exception:
                logger.exception("failed to update failed job state")
        time.sleep(0.1)


if __name__ == "__main__":
    run_worker()
