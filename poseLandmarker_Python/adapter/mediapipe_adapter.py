from __future__ import annotations

from pathlib import Path
from typing import Any

from schema.pose import (
    GpuDelegateUnavailableError,
    LandmarkerInitializationError,
    ModelAssetNotFoundError,
    PoseInferenceOptions,
)


class MediaPipeAdapter:
    def __init__(self) -> None:
        self._mp: Any | None = None
        self._vision: Any | None = None
        self._base_options_cls: Any | None = None
        self._landmarker: Any | None = None
        self._active_delegate = "CPU"

    def create_landmarker(self, options: PoseInferenceOptions) -> Any:
        model_path = Path(options.model_asset_path)
        if not model_path.exists():
            raise ModelAssetNotFoundError(f"MediaPipe model asset not found: {model_path}")

        self.close_landmarker()
        self._ensure_mediapipe()

        delegates = [options.delegate]
        if options.delegate == "GPU":
            delegates.append("CPU")

        last_error: Exception | None = None
        for delegate_name in delegates:
            try:
                landmarker_options = self._build_options(options, delegate_name)
                self._landmarker = self._vision.PoseLandmarker.create_from_options(landmarker_options)
                self._active_delegate = delegate_name
                return self._landmarker
            except Exception as exc:
                last_error = exc
                self.close_landmarker()
                if delegate_name == "GPU" and len(delegates) > 1:
                    continue
                break

        if options.delegate == "GPU" and self._active_delegate != "GPU" and last_error is not None:
            raise GpuDelegateUnavailableError(
                "Failed to initialize MediaPipe Pose Landmarker with GPU or CPU fallback."
            ) from last_error
        raise LandmarkerInitializationError("Failed to initialize MediaPipe Pose Landmarker.") from last_error

    def close_landmarker(self) -> None:
        if self._landmarker is not None:
            close = getattr(self._landmarker, "close", None)
            if callable(close):
                close()
            self._landmarker = None

    def detect(self, image: Any) -> Any:
        self._require_landmarker()
        return self._landmarker.detect(image)

    def detect_for_video(self, image: Any, timestamp_ms: int) -> Any:
        self._require_landmarker()
        return self._landmarker.detect_for_video(image, timestamp_ms)

    def detect_async(self, image: Any, timestamp_ms: int) -> None:
        self._require_landmarker()
        self._landmarker.detect_async(image, timestamp_ms)

    def to_mp_image(self, rgb_image: Any) -> Any:
        self._ensure_mediapipe()
        return self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb_image)

    def active_delegate(self) -> str:
        return self._active_delegate

    def _require_landmarker(self) -> None:
        if self._landmarker is None:
            raise LandmarkerInitializationError("MediaPipe Pose Landmarker is not initialized.")

    def _ensure_mediapipe(self) -> None:
        if self._mp is not None:
            return
        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision
        except ModuleNotFoundError as exc:
            raise LandmarkerInitializationError(
                "MediaPipe is not installed. Run `uv sync` in poseLandmarker_Python."
            ) from exc

        self._mp = mp
        self._vision = vision
        self._base_options_cls = mp.tasks.BaseOptions

    def _build_options(self, options: PoseInferenceOptions, delegate_name: str) -> Any:
        running_mode = getattr(self._vision.RunningMode, options.running_mode)
        delegate = self._resolve_delegate(delegate_name)
        base_options_kwargs = {"model_asset_path": str(options.model_asset_path)}
        if delegate is not None:
            base_options_kwargs["delegate"] = delegate
        base_options = self._base_options_cls(**base_options_kwargs)

        option_kwargs = dict(
            base_options=base_options,
            running_mode=running_mode,
            num_poses=options.num_poses,
            min_pose_detection_confidence=options.min_pose_detection_confidence,
            min_pose_presence_confidence=options.min_pose_presence_confidence,
            min_tracking_confidence=options.min_tracking_confidence,
            output_segmentation_masks=options.output_segmentation_masks,
        )
        if options.running_mode == "LIVE_STREAM" and options.result_callback is not None:
            option_kwargs["result_callback"] = options.result_callback
        return self._vision.PoseLandmarkerOptions(**option_kwargs)

    def _resolve_delegate(self, delegate_name: str) -> Any:
        delegate_enum = getattr(self._base_options_cls, "Delegate", None)
        if delegate_enum is None:
            return None
        return getattr(delegate_enum, delegate_name)
