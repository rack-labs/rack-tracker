class SkeletonMapperService:
    def map_landmarks(self, inference_results: list[dict]) -> dict:
        return {
            "frames": [],
            "videoInfo": {},
            "nextTimestampCursorMs": 0,
        }
