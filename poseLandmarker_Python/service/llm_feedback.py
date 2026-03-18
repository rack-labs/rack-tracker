class LlmFeedbackService:
    def generate(self, analysis: dict) -> dict:
        return {
            "version": "v1",
            "model": "pending",
            "overallComment": "",
            "highlights": [],
            "corrections": [],
            "coachCue": "",
        }
