from __future__ import annotations

from schema.frame import FrameExtractionResult
from schema.pose import PoseInferenceResult


class SkeletonMapperService:
    def map_landmarks(
        self,
        extraction_result: FrameExtractionResult,
        inference_result: PoseInferenceResult,
        display_name: str | None = None,
        requested_sampling_fps: float | None = None,
        effective_sampling_fps: float | None = None,
    ) -> dict:
        frame_results = [frame.to_dict() for frame in inference_result.frames]
        return {
            "frames": [
                {
                    "frameIndex": result["frameIndex"],
                    "timestampMs": result["timestampMs"],
                    "poseDetected": result["poseDetected"],
                    "landmarks": result["landmarks"],
                }
                for result in frame_results
            ],
            "videoInfo": {
                "videoSrc": str(extraction_result.source_path),
                "displayName": display_name or extraction_result.source_path.name,
                "sourceFps": extraction_result.source_fps,
                "frameCount": extraction_result.frame_count,
                "width": extraction_result.width,
                "height": extraction_result.height,
                "backend": extraction_result.backend,
                "extractedCount": extraction_result.extracted_count,
                "requestedSamplingFps": requested_sampling_fps,
                "effectiveSamplingFps": effective_sampling_fps or extraction_result.source_fps,
                "runningMode": inference_result.running_mode,
                "modelName": inference_result.model_name,
                "detectedFrameCount": inference_result.detected_frame_count,
            },
            "nextTimestampCursorMs": (
                frame_results[-1]["timestampMs"] + 1 if frame_results else 0
            ),
        }
