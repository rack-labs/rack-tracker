from __future__ import annotations


class AnalysisPipelineService:
    def analyze(self, skeleton: dict, exercise_type: str | None = None) -> dict:
        frames = skeleton.get("frames", [])
        video_info = skeleton.get("videoInfo", {})
        duration_ms = frames[-1]["timestampMs"] if frames else 0
        source_fps = float(video_info.get("sourceFps") or 0.0)
        extracted_count = int(video_info.get("extractedCount") or len(frames))
        sampled_fps = (extracted_count / max(duration_ms / 1000.0, 1.0)) if extracted_count else 0.0

        timeseries = [
            {
                "timestampMs": frame["timestampMs"],
                "poseDetected": frame["poseDetected"],
                "trackedPoints": len(frame.get("landmarks", [])),
            }
            for frame in frames
        ]

        events = []
        if frames:
            events = [
                {"type": "analysis_started", "timestampMs": frames[0]["timestampMs"]},
                {"type": "analysis_finished", "timestampMs": frames[-1]["timestampMs"]},
            ]

        return {
            "summary": {
                "exerciseType": exercise_type or "unknown",
                "frameCount": extracted_count,
                "durationMs": duration_ms,
                "sourceFps": source_fps,
                "sampledFps": round(sampled_fps, 2),
            },
            "kpis": [
                {"key": "frame_count", "label": "Extracted Frames", "value": extracted_count},
                {"key": "duration_ms", "label": "Duration (ms)", "value": round(duration_ms, 2)},
                {"key": "sampled_fps", "label": "Sampled FPS", "value": round(sampled_fps, 2)},
            ],
            "timeseries": timeseries,
            "events": events,
            "repSegments": [
                {
                    "repIndex": 1,
                    "startMs": frames[0]["timestampMs"] if frames else 0,
                    "endMs": frames[-1]["timestampMs"] if frames else 0,
                }
            ]
            if frames
            else [],
            "issues": []
            if frames
            else [
                {
                    "severity": "warning",
                    "code": "no_frames",
                    "message": "No frames were extracted from the requested video.",
                }
            ],
        }
