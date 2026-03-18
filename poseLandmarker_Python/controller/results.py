from fastapi import APIRouter

from schema.result import MotionAnalysisResult
from service.job_manager import job_manager

router = APIRouter(prefix="/jobs", tags=["results"])


@router.get("/{job_id}/result", response_model=MotionAnalysisResult)
def get_job_result(job_id: str) -> MotionAnalysisResult:
    return job_manager.get_result(job_id)
