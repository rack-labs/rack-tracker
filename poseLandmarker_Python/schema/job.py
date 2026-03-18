from pydantic import BaseModel


class JobProgress(BaseModel):
    stage: str
    currentStep: int
    totalSteps: int
    ratio: float


class JobError(BaseModel):
    code: str
    message: str


class JobCreateResponse(BaseModel):
    jobId: str
    status: str


class JobStatusResponse(BaseModel):
    jobId: str
    status: str
    progress: JobProgress | None = None
    error: JobError | None = None
