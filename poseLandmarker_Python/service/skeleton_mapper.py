from __future__ import annotations

from schema.frame import FrameExtractionResult


class SkeletonMapperService:
    def map_landmarks(
        self,
        extraction_result: FrameExtractionResult,
        inference_results: list[dict],
    ) -> dict:
        return {
            "frames": [
                {
                    "frameIndex": result["frameIndex"],
                    "timestampMs": result["timestampMs"],
                    "poseDetected": result["poseDetected"],
                    "landmarks": result["landmarks"],
                }
                for result in inference_results
            ],
            "videoInfo": {
                "videoSrc": str(extraction_result.source_path),
                "displayName": extraction_result.source_path.name,
                "sourceFps": extraction_result.source_fps,
                "frameCount": extraction_result.frame_count,
                "width": extraction_result.width,
                "height": extraction_result.height,
                "backend": extraction_result.backend,
                "extractedCount": extraction_result.extracted_count,
            },
            "nextTimestampCursorMs": (
                inference_results[-1]["timestampMs"] + 1 if inference_results else 0
            ),
        }
