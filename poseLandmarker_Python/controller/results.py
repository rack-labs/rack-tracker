from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from schema.result import MotionAnalysisSummary, SkeletonPageResponse
from service.job_manager import job_manager

router = APIRouter(prefix="/jobs", tags=["results"])


@router.get("/{job_id}/result", response_model=MotionAnalysisSummary)
def get_job_result(job_id: str) -> MotionAnalysisSummary:
    return job_manager.get_result(job_id)


@router.get("/{job_id}/skeleton", response_model=SkeletonPageResponse)
def get_job_skeleton_page(
    job_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=300),
) -> SkeletonPageResponse:
    return job_manager.get_skeleton_page(job_id, offset, limit)


@router.get("/{job_id}/skeleton/download")
def download_job_skeleton(job_id: str) -> FileResponse:
    skeleton_path = Path(job_manager.get_skeleton_download_path(job_id))
    return FileResponse(
        path=skeleton_path,
        media_type="application/octet-stream",
        filename=f"{job_id}.skeleton.json",
    )


@router.get("/{job_id}/benchmark")
def get_job_benchmark(job_id: str) -> dict:
    return job_manager.get_benchmark(job_id)


@router.get("/{job_id}/benchmark/frames")
def get_job_benchmark_frame_metrics(job_id: str) -> list[dict]:
    return job_manager.get_benchmark_frame_metrics(job_id)
