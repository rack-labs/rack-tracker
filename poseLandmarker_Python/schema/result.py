from pydantic import BaseModel, Field


class MotionAnalysisResult(BaseModel):
    skeleton: dict = Field(default_factory=dict)
    analysis: dict = Field(default_factory=dict)
    llmFeedback: dict = Field(default_factory=dict)
    benchmark: dict = Field(default_factory=dict)


class MotionAnalysisSummary(BaseModel):
    skeleton: dict = Field(default_factory=dict)
    analysis: dict = Field(default_factory=dict)
    llmFeedback: dict = Field(default_factory=dict)
    benchmark: dict = Field(default_factory=dict)


class SkeletonPageResponse(BaseModel):
    frames: list[dict] = Field(default_factory=list)
    videoInfo: dict = Field(default_factory=dict)
    nextTimestampCursorMs: float = 0
    offset: int = 0
    limit: int = 0
    totalFrames: int = 0
