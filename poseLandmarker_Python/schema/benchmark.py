from __future__ import annotations

from pydantic import BaseModel, Field


class BenchmarkStageStats(BaseModel):
    key: str
    label: str
    totalMs: float
    averageMs: float | None = None
    medianMs: float | None = None
    p95Ms: float | None = None
    shareRatio: float


class BenchmarkRunMetadata(BaseModel):
    benchmarkRunId: str
    sourceVideoPath: str
    videoFingerprint: str
    sourceVideoFps: float
    inferenceBackend: str
    requestedSamplingFps: float | None = None
    effectiveSamplingFps: float
    requestedDelegate: str
    actualDelegate: str
    delegateFallbackApplied: bool
    delegateErrors: dict[str, str] = Field(default_factory=dict)
    modelVariant: str
    runningMode: str
    frameCount: int
    sampleIntervalMs: float
    startedAt: str
    completedAt: str


class BenchmarkTimingSummary(BaseModel):
    frameExtractionMs: float
    rgbConversionMs: float
    inferenceMs: float
    serializationMs: float
    analysisMs: float
    totalElapsedMs: float
    stageStats: list[BenchmarkStageStats] = Field(default_factory=list)


class BenchmarkQualitySummary(BaseModel):
    poseDetectedRatio: float
    detectedFrameCount: int
    avgVisibility: float | None = None
    minVisibility: float | None = None
    lowVisibilityFrameRatio: float
    consecutiveMissedPoseMax: int
    analysisSuccess: bool


class BenchmarkFrameMetric(BaseModel):
    frameIndex: int
    timestampMs: float
    rgbConversionMs: float
    inferenceMs: float
    serializationMs: float
    totalFramePipelineMs: float
    poseDetected: bool
    landmarkCount: int
    avgVisibility: float | None = None
    minVisibility: float | None = None


class BenchmarkStorageRefs(BaseModel):
    summaryPath: str
    frameMetricsPath: str


class BenchmarkResult(BaseModel):
    run: BenchmarkRunMetadata
    timingSummary: BenchmarkTimingSummary
    qualitySummary: BenchmarkQualitySummary
    comparisonTags: list[str] = Field(default_factory=list)
    frameMetrics: list[BenchmarkFrameMetric] = Field(default_factory=list)
    storage: BenchmarkStorageRefs | None = None
