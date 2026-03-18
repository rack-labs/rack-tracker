from pydantic import BaseModel, Field


class MotionAnalysisResult(BaseModel):
    skeleton: dict = Field(default_factory=dict)
    analysis: dict = Field(default_factory=dict)
    llmFeedback: dict = Field(default_factory=dict)
