from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from config import (
    ALLOWED_VIDEO_EXTENSIONS,
    MOCK_VIDEO_BODYWEIGHT_KG,
    MOCK_VIDEO_EXERCISE_TYPE,
    MOCK_VIDEO_EXTERNAL_LOAD_KG,
    MOCK_VIDEO_PATH,
    UPLOAD_DIR,
)
from schema.result import MotionAnalysisSummary
from service.job_manager import job_manager

router = APIRouter(prefix="/analysis", tags=["analysis"])
EMPTY_FORM_SCHEMA = {"example": ""}


@router.post(
    "/preview",
    response_model=MotionAnalysisSummary,
    summary="Run Analysis Preview",
    description=(
        "Runs the full data-analysis pipeline immediately and returns the final analysis payload "
        "without creating a background job. If no video file is uploaded, the built-in sample "
        "video is used."
    ),
)
async def preview_analysis(
    video: UploadFile | None = File(default=None),
    fps: float | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    samplingFps: float | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    exerciseType: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    bodyweightKg: float | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    externalLoadKg: float | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    barPlacementMode: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    modelAssetPath: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    modelVariant: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
    delegate: str | None = Form(default=None, json_schema_extra=EMPTY_FORM_SCHEMA),
) -> MotionAnalysisSummary:
    source_path = str(MOCK_VIDEO_PATH)
    source_name = MOCK_VIDEO_PATH.name
    uses_mock_video = True

    if video is not None and video.filename:
        source_name = video.filename
        source_path = await _persist_upload(video)
        uses_mock_video = False

    if uses_mock_video:
        exerciseType = _resolve_optional_text(exerciseType) or MOCK_VIDEO_EXERCISE_TYPE
        bodyweightKg = bodyweightKg if bodyweightKg is not None else MOCK_VIDEO_BODYWEIGHT_KG
        externalLoadKg = (
            externalLoadKg if externalLoadKg is not None else MOCK_VIDEO_EXTERNAL_LOAD_KG
        )

    return await job_manager.preview(
        filename=source_name,
        source_path=source_path,
        requested_sampling_fps=samplingFps if samplingFps is not None else fps,
        exercise_type=exerciseType,
        bodyweight_kg=bodyweightKg,
        external_load_kg=externalLoadKg,
        bar_placement_mode=barPlacementMode,
        model_asset_path=modelAssetPath,
        model_variant=modelVariant,
        delegate=delegate,
    )


async def _persist_upload(video: UploadFile) -> str:
    filename = Path(video.filename or "upload.mp4").name
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported video file extension.")

    destination = UPLOAD_DIR / f"{uuid4().hex}_{filename}"
    content = await video.read()
    destination.write_bytes(content)
    return str(destination)


def _resolve_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized
