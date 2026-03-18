class AnalysisPipelineService:
    def analyze(self, skeleton: dict) -> dict:
        return {
            "summary": {},
            "kpis": [],
            "timeseries": [],
            "events": [],
            "repSegments": [],
            "issues": [],
        }
