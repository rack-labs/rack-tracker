class LlmFeedbackService:
    def generate(self, analysis: dict) -> dict:
        summary = analysis.get("summary", {})
        frame_count = int(summary.get("frameCount") or 0)
        sampled_fps = summary.get("sampledFps") or 0
        exercise_type = summary.get("exerciseType") or "unknown"

        return {
            "version": "v1",
            "model": "rule-based-placeholder",
            "overallComment": f"{exercise_type} video processed with {frame_count} sampled frames.",
            "highlights": [
                f"OpenCV frame extraction completed successfully at approximately {sampled_fps} FPS."
            ]
            if frame_count
            else ["Frame extraction did not yield usable frames."],
            "corrections": []
            if frame_count
            else ["Check the input video path, codec support, and sampling options."],
            "coachCue": "Use this placeholder feedback until the LLM integration is connected.",
        }
