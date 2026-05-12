from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import Report
from app.services.queue import JobStore
from app.services.redis_client import get_redis


router = APIRouter(prefix="/api/reports", tags=["reports"])


def get_store() -> JobStore:
    return JobStore(get_redis())


@router.get("/{report_id}", response_model=Report)
def get_report(report_id: str, store: JobStore = Depends(get_store)) -> Report:
    report = store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or expired.")
    return report
