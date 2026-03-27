from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

RunningMode = Literal["IMAGE", "VIDEO", "LIVE_STREAM"]
ModelVariant = Literal["lite", "full", "heavy"]
Delegate = Literal["GPU", "CPU"]


class PoseInferenceServiceError(Exception):
    pass


class ModelAssetNotFoundError(PoseInferenceServiceError):
    pass


class LandmarkerInitializationError(PoseInferenceServiceError):
    pass


class GpuDelegateUnavailableError(LandmarkerInitializationError):
    pass


class InvalidFrameInputError(PoseInferenceServiceError):
    pass


class PoseInferenceError(PoseInferenceServiceError):
    pass


class ResultSerializationError(PoseInferenceServiceError):
    pass


@dataclass(slots=True)
class PoseInferenceOptions:
    model_asset_path: Path
    model_variant: ModelVariant = "full"
    running_mode: RunningMode = "VIDEO"
    delegate: Delegate = "GPU"
    num_poses: int = 1
    min_pose_detection_confidence: float = 0.5
    min_pose_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    output_segmentation_masks: bool = False
    result_callback: object | None = None


@dataclass(slots=True)
class PoseLandmarkPoint:
    name: str
    x: float
    y: float
    z: float
    visibility: float | None = None
    presence: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class PoseFrameBenchmark:
    frame_index: int
    timestamp_ms: float
    rgb_conversion_ms: float
    inference_ms: float
    serialization_ms: float
    total_frame_pipeline_ms: float
    pose_detected: bool
    landmark_count: int
    avg_visibility: float | None = None
    min_visibility: float | None = None

    def to_dict(self) -> dict:
        return {
            "frameIndex": self.frame_index,
            "timestampMs": self.timestamp_ms,
            "rgbConversionMs": self.rgb_conversion_ms,
            "inferenceMs": self.inference_ms,
            "serializationMs": self.serialization_ms,
            "totalFramePipelineMs": self.total_frame_pipeline_ms,
            "poseDetected": self.pose_detected,
            "landmarkCount": self.landmark_count,
            "avgVisibility": self.avg_visibility,
            "minVisibility": self.min_visibility,
        }


@dataclass(slots=True)
class PoseFrameResult:
    frame_index: int
    timestamp_ms: float
    pose_detected: bool
    landmarks: list[PoseLandmarkPoint]
    world_landmarks: list[PoseLandmarkPoint] | None = None
    segmentation_mask: object | None = None
    benchmark: PoseFrameBenchmark | None = None

    def to_dict(self) -> dict:
        return {
            "frameIndex": self.frame_index,
            "timestampMs": self.timestamp_ms,
            "poseDetected": self.pose_detected,
            "landmarks": [landmark.to_dict() for landmark in self.landmarks],
        }


@dataclass(slots=True)
class PoseInferenceResult:
    source_path: str
    running_mode: RunningMode
    model_name: str
    frame_count: int
    detected_frame_count: int
    requested_delegate: Delegate
    actual_delegate: Delegate
    delegate_fallback_applied: bool
    delegate_errors: dict[str, str]
    frames: list[PoseFrameResult]
