from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


FloatSeries = list[float]
OptionalFloatSeries = list[float | None]


class AnalysisSummary(BaseModel):
    exerciseType: str = "unknown"
    repCount: int = 0
    frameCount: int = 0
    durationMs: float = 0.0
    sourceFps: float = 0.0
    sampledFps: float = 0.0
    detectionRatio: float = 0.0
    usableFrameCount: int = 0
    bodyweightKg: float | None = None
    externalLoadKg: float | None = None
    barPlacementMode: str | None = None
    barPlacementResolved: str | None = None
    totalSystemMassKg: float | None = None


class BodyProfileResult(BaseModel):
    leftFemurLen: float = 0.0
    rightFemurLen: float = 0.0
    leftTibiaLen: float = 0.0
    rightTibiaLen: float = 0.0
    torsoLen: float = 0.0
    leftUpperArmLen: float = 0.0
    rightUpperArmLen: float = 0.0
    femurToTorsoRatio: float = 0.0
    tibiaToFemurRatio: float = 0.0
    limbAsymmetry: dict[str, float] = Field(default_factory=dict)
    jointAngleBaselineDeg: dict[str, float] = Field(default_factory=dict)
    sampleFrameCount: int = 0


class GroundRefResult(BaseModel):
    groundY: float = 0.0
    midFootX: float = 0.0
    footWidth: float = 0.0
    sagittalFootLength: float | None = None
    leftFootVec: list[float] = Field(default_factory=list)
    rightFootVec: list[float] = Field(default_factory=list)
    sampleFrameCount: int = 0
    viewType: str = "unknown"
    viewConfidence: float = 0.0
    viewSignals: dict[str, float] = Field(default_factory=dict)
    barPlacementInput: str | None = None
    barPlacementResolved: str | None = None
    bodyweightKg: float | None = None
    externalLoadKg: float | None = None
    totalSystemMassKg: float | None = None


class KPIResult(BaseModel):
    key: str = ""
    label: str = ""
    value: float = 0.0
    unit: str = ""
    description: str = ""
    personalContext: str | None = None


class TimeseriesResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamps_ms: FloatSeries = Field(default_factory=list)
    bar_placement_input: str | None = None
    bar_placement_resolved: str | None = None
    hip_height: FloatSeries = Field(default_factory=list)
    bar_x: FloatSeries = Field(default_factory=list)
    bar_y: FloatSeries = Field(default_factory=list)
    bar_confidence: FloatSeries = Field(default_factory=list)
    bar_com_offset: OptionalFloatSeries = Field(default_factory=list)
    body_com_x: FloatSeries = Field(default_factory=list)
    body_com_y: FloatSeries = Field(default_factory=list)
    com_x: FloatSeries = Field(default_factory=list)
    com_y: FloatSeries = Field(default_factory=list)
    cop_ap_normalized: OptionalFloatSeries = Field(default_factory=list)
    cop_ml_normalized: OptionalFloatSeries = Field(default_factory=list)
    bar_over_midfoot: OptionalFloatSeries = Field(default_factory=list)


class RepSegmentResult(BaseModel):
    repIndex: int = 0
    startMs: float = 0.0
    endMs: float = 0.0
    bottomMs: float = 0.0
    phaseEccentricMs: float = 0.0
    phaseConcentricMs: float = 0.0
    depthAngleDeg: float = 0.0


class EventResult(BaseModel):
    type: str = ""
    timestampMs: float = 0.0
    repIndex: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IssueResult(BaseModel):
    severity: str = ""
    code: str = ""
    message: str = ""
    timestampMs: float | None = None
    repIndex: int | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    summary: AnalysisSummary = Field(default_factory=AnalysisSummary)
    bodyProfile: BodyProfileResult = Field(default_factory=BodyProfileResult)
    groundRef: GroundRefResult = Field(default_factory=GroundRefResult)
    kpis: list[KPIResult] = Field(default_factory=list)
    timeseries: TimeseriesResult = Field(default_factory=TimeseriesResult)
    repSegments: list[RepSegmentResult] = Field(default_factory=list)
    events: list[EventResult] = Field(default_factory=list)
    issues: list[IssueResult] = Field(default_factory=list)
    visualization: dict[str, Any] = Field(default_factory=dict)


class LlmFeedbackResult(BaseModel):
    version: str = ""
    model: str = ""
    overallComment: str = ""
    highlights: list[str] = Field(default_factory=list)
    corrections: list[str] = Field(default_factory=list)
    coachCue: str = ""


class MotionAnalysisResult(BaseModel):
    skeleton: dict[str, Any] = Field(default_factory=dict)
    analysis: AnalysisResult = Field(default_factory=AnalysisResult)
    llmFeedback: LlmFeedbackResult = Field(default_factory=LlmFeedbackResult)
    benchmark: dict[str, Any] = Field(default_factory=dict)


class MotionAnalysisSummary(BaseModel):
    skeleton: dict[str, Any] = Field(default_factory=dict)
    analysis: AnalysisResult = Field(default_factory=AnalysisResult)
    llmFeedback: LlmFeedbackResult = Field(default_factory=LlmFeedbackResult)
    benchmark: dict[str, Any] = Field(default_factory=dict)


class SkeletonPageResponse(BaseModel):
    frames: list[dict[str, Any]] = Field(default_factory=list)
    videoInfo: dict[str, Any] = Field(default_factory=dict)
    nextTimestampCursorMs: float = 0
    offset: int = 0
    limit: int = 0
    totalFrames: int = 0
