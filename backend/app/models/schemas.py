from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., min_length=12, max_length=300)


class AnalyzeResponse(BaseModel):
    job_id: str
    report_url: str | None = None
    cached: bool = False


class JobState(BaseModel):
    id: str
    repo_url: str
    normalized_repo: str
    status: Literal["queued", "running", "completed", "failed"]
    step: str
    progress: int = Field(ge=0, le=100)
    error: str | None = None
    report_id: str | None = None


class ScoreBreakdown(BaseModel):
    size: int
    complexity: int
    duplication: int
    activity: int
    dependencies: int
    readme: int


class Report(BaseModel):
    id: str
    repo_url: str
    normalized_repo: str
    analyzed_at: str
    language: str
    score: int
    score_breakdown: ScoreBreakdown
    summary: dict[str, Any]
    static_analysis: dict[str, Any]
    git_history: dict[str, Any]
    dependencies: dict[str, Any]
    readme_quality: dict[str, Any]
