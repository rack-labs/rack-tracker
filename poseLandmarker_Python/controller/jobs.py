from fastapi import APIRouter, File, Form, UploadFile

from schema.job import JobCreateResponse, JobStatusResponse
from service.job_manager import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse)
async def create_job(
    video: UploadFile = File(...),
    fps: float = Form(...),
    exerciseType: str | None = Form(default=None),
) -> JobCreateResponse:
    return await job_manager.create_job(
        filename=video.filename or "uploaded-video",
        fps=fps,
        exercise_type=exerciseType,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    return job_manager.get_status(job_id)
