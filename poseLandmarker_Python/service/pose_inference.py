from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from time import perf_counter
from typing import Any

from adapter.mediapipe_adapter import MediaPipeAdapter
from config import DEFAULT_MODEL_ASSET_PATH, DEFAULT_MODEL_VARIANT
from schema.frame import ExtractedFrame
from schema.pose import (
    InvalidFrameInputError,
    PoseFrameBenchmark,
    PoseFrameResult,
    PoseInferenceError,
    PoseInferenceOptions,
    PoseInferenceResult,
    PoseLandmarkPoint,
    ResultSerializationError,
)

POSE_LANDMARK_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]


class PoseInferenceService:
    def __init__(self, adapter: MediaPipeAdapter | None = None) -> None:
        self._adapter = adapter or MediaPipeAdapter()

    def infer(
        self,
        frames: list[ExtractedFrame],
        options: PoseInferenceOptions | None = None,
        source_path: str = "",
    ) -> list[dict]:
        result = self.run(frames=frames, options=options, source_path=source_path)
        return [frame.to_dict() for frame in result.frames]

    def run(
        self,
        frames: list[ExtractedFrame],
        options: PoseInferenceOptions | None = None,
        source_path: str = "",
    ) -> PoseInferenceResult:
        resolved_options = options or self._default_options()
        frame_results = list(self.iter_infer(frames=frames, options=resolved_options))
        actual_delegate = self._adapter.active_delegate()
        return PoseInferenceResult(
            source_path=source_path,
            running_mode=resolved_options.running_mode,
            model_name=Path(resolved_options.model_asset_path).name,
            frame_count=len(frames),
            detected_frame_count=sum(1 for frame in frame_results if frame.pose_detected),
            requested_delegate=resolved_options.delegate,
            actual_delegate=actual_delegate,  # type: ignore[arg-type]
            delegate_fallback_applied=resolved_options.delegate != actual_delegate,
            frames=frame_results,
        )

    def iter_infer(
        self,
        frames: Iterable[ExtractedFrame],
        options: PoseInferenceOptions | None = None,
    ) -> Iterator[PoseFrameResult]:
        resolved_options = options or self._default_options()
        self._adapter.create_landmarker(resolved_options)
        try:
            for frame in frames:
                yield self._infer_frame(frame, resolved_options)
        finally:
            self._adapter.close_landmarker()

    def _infer_frame(
        self,
        frame: ExtractedFrame,
        options: PoseInferenceOptions,
    ) -> PoseFrameResult:
        if frame.image is None:
            raise InvalidFrameInputError(f"Frame image is missing for frame {frame.index}.")

        frame_started = perf_counter()
        rgb_started = perf_counter()
        rgb_image = self._ensure_rgb(frame.image)
        mp_image = self._adapter.to_mp_image(rgb_image)
        rgb_conversion_ms = (perf_counter() - rgb_started) * 1000.0
        timestamp_ms = max(0, int(round(frame.timestamp_ms)))

        try:
            inference_started = perf_counter()
            if options.running_mode == "IMAGE":
                raw_result = self._adapter.detect(mp_image)
            elif options.running_mode == "VIDEO":
                raw_result = self._adapter.detect_for_video(mp_image, timestamp_ms)
            elif options.running_mode == "LIVE_STREAM":
                self._adapter.detect_async(mp_image, timestamp_ms)
                raise PoseInferenceError(
                    "LIVE_STREAM mode is not supported by the synchronous batch pipeline."
                )
            else:
                raise PoseInferenceError(f"Unsupported running mode: {options.running_mode}")
            inference_ms = (perf_counter() - inference_started) * 1000.0
        except Exception as exc:
            if isinstance(exc, PoseInferenceError):
                raise
            raise PoseInferenceError(f"Pose inference failed for frame {frame.index}.") from exc

        serialization_started = perf_counter()
        frame_result = self._serialize_result(
            frame_index=frame.index,
            timestamp_ms=frame.timestamp_ms,
            raw_result=raw_result,
        )
        serialization_ms = (perf_counter() - serialization_started) * 1000.0
        visibility_values = [
            landmark.visibility for landmark in frame_result.landmarks if landmark.visibility is not None
        ]
        frame_result.benchmark = PoseFrameBenchmark(
            frame_index=frame.index,
            timestamp_ms=frame.timestamp_ms,
            rgb_conversion_ms=round(rgb_conversion_ms, 3),
            inference_ms=round(inference_ms, 3),
            serialization_ms=round(serialization_ms, 3),
            total_frame_pipeline_ms=round((perf_counter() - frame_started) * 1000.0, 3),
            pose_detected=frame_result.pose_detected,
            landmark_count=len(frame_result.landmarks),
            avg_visibility=round(sum(visibility_values) / len(visibility_values), 4)
            if visibility_values
            else None,
            min_visibility=round(min(visibility_values), 4) if visibility_values else None,
        )
        return frame_result

    def _serialize_result(
        self,
        frame_index: int,
        timestamp_ms: float,
        raw_result: Any,
    ) -> PoseFrameResult:
        try:
            pose_landmarks = list(getattr(raw_result, "pose_landmarks", []) or [])
        except Exception as exc:
            raise ResultSerializationError("Failed to access pose landmark results.") from exc

        if not pose_landmarks:
            return PoseFrameResult(
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
                pose_detected=False,
                landmarks=[],
            )

        first_pose = pose_landmarks[0]
        landmarks = [
            self._serialize_landmark(name=name, landmark=landmark)
            for name, landmark in zip(POSE_LANDMARK_NAMES, first_pose)
        ]
        return PoseFrameResult(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            pose_detected=True,
            landmarks=landmarks,
        )

    def _serialize_landmark(self, name: str, landmark: Any) -> PoseLandmarkPoint:
        return PoseLandmarkPoint(
            name=name,
            x=round(float(getattr(landmark, "x")), 6),
            y=round(float(getattr(landmark, "y")), 6),
            z=round(float(getattr(landmark, "z")), 6),
            visibility=self._optional_float(getattr(landmark, "visibility", None)),
            presence=self._optional_float(getattr(landmark, "presence", None)),
        )

    def _optional_float(self, value: object) -> float | None:
        if value is None:
            return None
        return round(float(value), 6)

    def _ensure_rgb(self, image: Any) -> Any:
        shape = getattr(image, "shape", None)
        if not shape or len(shape) < 3 or shape[2] != 3:
            raise InvalidFrameInputError("Expected a 3-channel frame image.")
        return image[:, :, ::-1]

    def _default_options(self) -> PoseInferenceOptions:
        return PoseInferenceOptions(
            model_asset_path=DEFAULT_MODEL_ASSET_PATH,
            model_variant=DEFAULT_MODEL_VARIANT,
        )
