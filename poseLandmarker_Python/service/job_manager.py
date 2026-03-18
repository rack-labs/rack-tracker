from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from config import EXTRACTED_FRAME_DIR
from schema.frame import FrameExtractionOptions
from schema.job import JobCreateResponse, JobProgress, JobStatusResponse
from schema.result import MotionAnalysisResult
from service.analysis_pipeline import AnalysisPipelineService
from service.llm_feedback import LlmFeedbackService
from service.pose_inference import PoseInferenceService
from service.skeleton_mapper import SkeletonMapperService
from service.video_reader import VideoReaderService


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
        self._video_reader = VideoReaderService()
        self._pose_inference = PoseInferenceService()
        self._skeleton_mapper = SkeletonMapperService()
        self._analysis_pipeline = AnalysisPipelineService()
        self._llm_feedback = LlmFeedbackService()

    async def create_job(
        self,
        filename: str,
        source_path: str,
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
                    "videoSrc": source_path,
                    "displayName": filename,
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
                "sourcePath": source_path,
                "fps": fps,
                "exerciseType": exercise_type,
            },
        )
        asyncio.create_task(self._run_job(job_id))
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
        if job.status != "completed" or job.result is None:
            raise HTTPException(status_code=409, detail="Job result is not ready.")
        return job.result

    async def _run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        try:
            self._set_progress(job, "extracting", 1, 4, 0.25)
            extraction_result = await asyncio.to_thread(self._extract_frames, job)

            inference_results = self._pose_inference.infer(extraction_result.frames)
            skeleton = self._skeleton_mapper.map_landmarks(extraction_result, inference_results)
            job.result = MotionAnalysisResult(
                skeleton=skeleton,
                analysis={},
                llmFeedback={},
            )

            self._set_progress(job, "analyzing", 2, 4, 0.75)
            analysis = self._analysis_pipeline.analyze(
                skeleton=skeleton,
                exercise_type=job.metadata.get("exerciseType"),
            )
            job.result.analysis = analysis

            self._set_progress(job, "generating_feedback", 3, 4, 0.9)
            job.result.llmFeedback = self._llm_feedback.generate(analysis)

            self._set_progress(job, "completed", 4, 4, 1.0)
            job.status = "completed"
        except Exception as exc:
            self._fail_job(job, exc)

    def _extract_frames(self, job: JobRecord):
        source_path = Path(str(job.metadata["sourcePath"]))
        fps = float(job.metadata["fps"])
        options = FrameExtractionOptions(
            video_path=source_path,
            sampling_mode="target_fps",
            target_fps=fps,
            output_dir=EXTRACTED_FRAME_DIR / job.job_id,
            save_images=False,
            convert_bgr_to_rgb=False,
        )
        return self._video_reader.extract_frames(options)

    def _set_progress(
        self,
        job: JobRecord,
        stage: str,
        current_step: int,
        total_steps: int,
        ratio: float,
    ) -> None:
        job.status = stage
        job.progress = JobProgress(
            stage=stage,
            currentStep=current_step,
            totalSteps=total_steps,
            ratio=ratio,
        )

    def _fail_job(self, job: JobRecord, exc: Exception) -> None:
        job.status = "failed"
        job.progress = JobProgress(
            stage="failed",
            currentStep=0,
            totalSteps=4,
            ratio=0.0,
        )
        job.error = {
            "code": exc.__class__.__name__,
            "message": str(exc),
        }


job_manager = JobManager()
