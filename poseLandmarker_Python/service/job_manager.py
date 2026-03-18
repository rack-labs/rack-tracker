from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from schema.job import JobCreateResponse, JobProgress, JobStatusResponse
from schema.result import MotionAnalysisResult


@dataclass
class JobRecord:
    job_id: str
    status: str
    progress: JobProgress | None = None
    error: dict[str, Any] | None = None
    result: MotionAnalysisResult | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    async def create_job(
        self,
        filename: str,
        fps: float,
        exercise_type: str | None,
    ) -> JobCreateResponse:
        job_id = f"job_{uuid4().hex[:8]}"
        progress = JobProgress(
            stage="queued",
            currentStep=0,
            totalSteps=4,
            ratio=0.0,
        )
        result = MotionAnalysisResult(
            skeleton={
                "frames": [],
                "videoInfo": {
                    "videoSrc": filename,
                    "fps": fps,
                },
                "nextTimestampCursorMs": 0,
            },
            analysis={
                "summary": {
                    "exerciseType": exercise_type or "unknown",
                },
                "kpis": [],
                "timeseries": [],
                "events": [],
                "repSegments": [],
                "issues": [],
            },
            llmFeedback={},
        )
        self._jobs[job_id] = JobRecord(
            job_id=job_id,
            status="queued",
            progress=progress,
            result=result,
            metadata={
                "filename": filename,
                "fps": fps,
                "exerciseType": exercise_type,
            },
        )
        return JobCreateResponse(jobId=job_id, status="queued")

    def get_status(self, job_id: str) -> JobStatusResponse:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return JobStatusResponse(
            jobId=job.job_id,
            status=job.status,
            progress=job.progress,
            error=job.error,
        )

    def get_result(self, job_id: str) -> MotionAnalysisResult:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.result is None:
            raise HTTPException(status_code=409, detail="Job result is not ready.")
        return job.result


job_manager = JobManager()
