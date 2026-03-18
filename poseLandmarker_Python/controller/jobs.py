from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import ALLOWED_VIDEO_EXTENSIONS, MOCK_VIDEO_PATH, UPLOAD_DIR
from schema.job import JobCreateResponse, JobStatusResponse
from service.job_manager import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse)
async def create_job(
    video: UploadFile | None = File(default=None),
    fps: float = Form(...),
    exerciseType: str | None = Form(default=None),
) -> JobCreateResponse:
    source_path = str(MOCK_VIDEO_PATH)
    source_name = MOCK_VIDEO_PATH.name

    if video is not None and video.filename:
        source_name = video.filename
        source_path = await _persist_upload(video)

    return await job_manager.create_job(
        filename=source_name,
        source_path=source_path,
        fps=fps,
        exercise_type=exerciseType,
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    return job_manager.get_status(job_id)


async def _persist_upload(video: UploadFile) -> str:
    filename = Path(video.filename or "upload.mp4").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported video file extension.")

    destination = UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    content = await video.read()
    destination.write_bytes(content)
    return str(destination)
