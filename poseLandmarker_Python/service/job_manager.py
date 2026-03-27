from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from config import DEFAULT_MODEL_ASSET_PATH, DEFAULT_MODEL_VARIANT, EXTRACTED_FRAME_DIR, MODEL_ASSET_PATHS
from schema.frame import FrameExtractionOptions
from schema.job import JobCreateResponse, JobProgress, JobStatusResponse
from schema.pose import PoseInferenceOptions
from schema.result import MotionAnalysisResult
from service.analysis_pipeline import AnalysisPipelineService
from service.benchmarking import BenchmarkService
from service.llm_feedback import LlmFeedbackService
from service.pose_inference import PoseInferenceService
from service.skeleton_mapper import SkeletonMapperService
from service.video_reader import VideoReaderService

VALID_MODEL_VARIANTS = {"lite", "full", "heavy"}
VALID_DELEGATES = {"CPU", "GPU"}


@dataclass
class JobRecord:
    job_id: str
    status: str
    progress: JobProgress | None = None
    error: dict[str, Any] | None = None
    result: MotionAnalysisResult | None = None
    benchmark: dict[str, Any] | None = None
    benchmark_frame_metrics: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._video_reader = VideoReaderService()
        self._pose_inference = PoseInferenceService()
        self._skeleton_mapper = SkeletonMapperService()
        self._analysis_pipeline = AnalysisPipelineService()
        self._llm_feedback = LlmFeedbackService()
        self._benchmark_service = BenchmarkService()

    async def create_job(
        self,
        filename: str,
        source_path: str,
        fps: float,
        exercise_type: str | None,
        model_asset_path: str | None = None,
        model_variant: str | None = None,
        delegate: str | None = None,
    ) -> JobCreateResponse:
        job_id = f"job_{uuid4().hex[:8]}"
        metadata = {
            "filename": filename,
            "sourcePath": source_path,
            "fps": fps,
            "exerciseType": exercise_type,
            "modelAssetPath": model_asset_path,
            "modelVariant": model_variant,
            "delegate": delegate,
        }
        # Validate user-provided inference overrides before enqueuing the job.
        self._build_inference_options_from_metadata(metadata)
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
            benchmark={},
        )
        self._jobs[job_id] = JobRecord(
            job_id=job_id,
            status="queued",
            progress=progress,
            result=result,
            metadata=metadata,
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

    def get_benchmark(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.status != "completed" or job.benchmark is None:
            raise HTTPException(status_code=409, detail="Benchmark result is not ready.")
        return job.benchmark

    def get_benchmark_frame_metrics(self, job_id: str) -> list[dict[str, Any]]:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.status != "completed":
            raise HTTPException(status_code=409, detail="Benchmark frame metrics are not ready.")
        return job.benchmark_frame_metrics

    async def _run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        started_at = datetime.now(timezone.utc)
        total_started = perf_counter()
        try:
            self._set_progress(job, "extracting", 1, 4, 0.25)
            extraction_started = perf_counter()
            extraction_options, extraction_result = await asyncio.to_thread(self._extract_frames, job)
            frame_extraction_ms = (perf_counter() - extraction_started) * 1000.0

            inference_options = self._build_inference_options(job)
            inference_result = self._pose_inference.run(
                frames=extraction_result.frames,
                options=inference_options,
                source_path=str(extraction_result.source_path),
            )
            skeleton = self._skeleton_mapper.map_landmarks(
                extraction_result,
                inference_result,
                display_name=str(job.metadata.get("filename") or extraction_result.source_path.name),
            )
            job.result = MotionAnalysisResult(
                skeleton=skeleton,
                analysis={},
                llmFeedback={},
                benchmark={},
            )

            self._set_progress(job, "analyzing", 2, 4, 0.75)
            analysis_started = perf_counter()
            analysis = self._analysis_pipeline.analyze(
                skeleton=skeleton,
                exercise_type=job.metadata.get("exerciseType"),
            )
            analysis_ms = (perf_counter() - analysis_started) * 1000.0
            job.result.analysis = analysis

            benchmark_result = self._benchmark_service.build_result(
                benchmark_run_id=f"benchmark_{job.job_id}",
                source_video_path=str(extraction_result.source_path),
                extraction_options=extraction_options,
                extraction_result=extraction_result,
                inference_result=inference_result,
                analysis_result=analysis,
                frame_extraction_ms=frame_extraction_ms,
                analysis_ms=analysis_ms,
                total_elapsed_ms=(perf_counter() - total_started) * 1000.0,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            job.benchmark = benchmark_result.model_dump(exclude={"frameMetrics"})
            job.benchmark_frame_metrics = [
                frame_metric.model_dump() for frame_metric in benchmark_result.frameMetrics
            ]
            job.result.benchmark = job.benchmark

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
        return options, self._video_reader.extract_frames(options)

    def _build_inference_options(self, job: JobRecord) -> PoseInferenceOptions | None:
        return self._build_inference_options_from_metadata(job.metadata)

    def _build_inference_options_from_metadata(
        self,
        metadata: dict[str, Any],
    ) -> PoseInferenceOptions | None:
        raw_model_asset_path = self._normalize_optional_text(metadata.get("modelAssetPath"))
        raw_model_variant = self._normalize_optional_text(metadata.get("modelVariant"))
        raw_delegate = self._normalize_optional_text(metadata.get("delegate"))
        if not raw_model_asset_path and not raw_model_variant and not raw_delegate:
            return None

        model_variant = str(raw_model_variant or DEFAULT_MODEL_VARIANT).lower()
        if model_variant not in VALID_MODEL_VARIANTS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid modelVariant '{model_variant}'. Use one of: lite, full, heavy.",
            )

        resolved_model_path = (
            Path(str(raw_model_asset_path))
            if raw_model_asset_path
            else MODEL_ASSET_PATHS.get(model_variant, DEFAULT_MODEL_ASSET_PATH)
        )
        options = PoseInferenceOptions(
            model_asset_path=resolved_model_path,
            model_variant=model_variant,  # type: ignore[arg-type]
        )
        if raw_delegate:
            delegate = str(raw_delegate).upper()
            if delegate not in VALID_DELEGATES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid delegate '{raw_delegate}'. Use CPU or GPU.",
                )
            options.delegate = delegate  # type: ignore[assignment]
        return options

    def _normalize_optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        if normalized.lower() == "string":
            return None
        return normalized

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
