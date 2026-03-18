from __future__ import annotations

from schema.frame import ExtractedFrame


class PoseInferenceService:
    def infer(self, frames: list[ExtractedFrame]) -> list[dict]:
        results: list[dict] = []
        for frame in frames:
            width = max(frame.width, 1)
            height = max(frame.height, 1)
            center_x = frame.width / 2.0
            center_y = frame.height / 2.0
            results.append(
                {
                    "frameIndex": frame.index,
                    "timestampMs": frame.timestamp_ms,
                    "poseDetected": True,
                    "landmarks": [
                        self._landmark("nose", center_x, height * 0.18, width, height, 0.98),
                        self._landmark("left_shoulder", width * 0.36, height * 0.32, width, height, 0.94),
                        self._landmark("right_shoulder", width * 0.64, height * 0.32, width, height, 0.94),
                        self._landmark("left_hip", width * 0.43, center_y, width, height, 0.92),
                        self._landmark("right_hip", width * 0.57, center_y, width, height, 0.92),
                        self._landmark("left_knee", width * 0.45, height * 0.72, width, height, 0.9),
                        self._landmark("right_knee", width * 0.55, height * 0.72, width, height, 0.9),
                    ],
                }
            )
        return results

    def _landmark(
        self,
        name: str,
        x: float,
        y: float,
        width: int,
        height: int,
        visibility: float,
    ) -> dict:
        return {
            "name": name,
            "x": round(x / width, 6),
            "y": round(y / height, 6),
            "z": 0.0,
            "visibility": visibility,
        }
