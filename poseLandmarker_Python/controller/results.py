from fastapi import APIRouter

from schema.result import MotionAnalysisResult
from service.job_manager import job_manager

router = APIRouter(prefix="/jobs", tags=["results"])


@router.get("/{job_id}/result", response_model=MotionAnalysisResult)
def get_job_result(job_id: str) -> MotionAnalysisResult:
    return job_manager.get_result(job_id)


@router.get("/{job_id}/benchmark")
def get_job_benchmark(job_id: str) -> dict:
    return job_manager.get_benchmark(job_id)


@router.get("/{job_id}/benchmark/frames")
def get_job_benchmark_frame_metrics(job_id: str) -> list[dict]:
    return job_manager.get_benchmark_frame_metrics(job_id)
