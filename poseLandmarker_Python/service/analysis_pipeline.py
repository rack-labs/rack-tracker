from __future__ import annotations

from service.analysis_body_profile import extract_body_profile
from service.analysis_cop import detect_view, extract_cop
from service.analysis_events import detect_events
from service.analysis_features import extract_features
from service.analysis_issues import detect_issues
from service.analysis_kpis import calc_kpis
from service.analysis_preprocess import preprocess
from service.analysis_reps import detect_reps
from service.analysis_thresholds import build_personal_thresholds
from service.analysis_visualization import build_visualization


class AnalysisPipelineService:
    def analyze(
        self,
        skeleton: dict,
        exercise_type: str | None = None,
        bodyweight_kg: float | None = None,
        external_load_kg: float | None = None,
        bar_placement_mode: str | None = None,
    ) -> dict:
        resolved_exercise_type = self._resolve_exercise_type(exercise_type)
        frames_raw = skeleton.get("frames", [])
        video_info = skeleton.get("videoInfo", {})

        clean_frames = preprocess(frames_raw)
        body_profile = extract_body_profile(clean_frames)
        view_inference = detect_view(clean_frames)
        resolved_bar_placement_mode = bar_placement_mode or "high_bar"
        features = extract_features(
            clean_frames,
            body_profile,
            bar_placement_mode=resolved_bar_placement_mode,
        )
        ground_ref, features = extract_cop(
            clean_frames,
            features,
            view_inference,
            bodyweight_kg=bodyweight_kg,
            external_load_kg=external_load_kg,
        )
        rep_segments = detect_reps(features, exercise_type=resolved_exercise_type)
        kpis = calc_kpis(features, rep_segments, body_profile, ground_ref)
        kpi_map = {kpi.key: kpi.value for kpi in kpis}
        thresholds = build_personal_thresholds(body_profile, rep_segments, kpi_map, ground_ref)
        events = detect_events(frames_raw, rep_segments)
        summary = self._build_summary(
            frames_raw,
            clean_frames,
            video_info,
            resolved_exercise_type,
            len(rep_segments),
            bodyweight_kg,
            external_load_kg,
            resolved_bar_placement_mode,
            features.bar_placement_resolved,
        )
        issues = detect_issues(rep_segments, kpis, body_profile, ground_ref, summary, thresholds)
        visualization = build_visualization(
            clean_frames,
            features,
            ground_ref,
            rep_segments,
            thresholds,
        )

        return {
            "summary": summary,
            "bodyProfile": body_profile.to_dict(),
            "groundRef": ground_ref.to_dict(),
            "kpis": [kpi.to_dict() for kpi in kpis],
            "timeseries": features.to_timeseries_dict(),
            "repSegments": [segment.to_dict() for segment in rep_segments],
            "events": [event.to_dict() for event in events],
            "issues": [issue.to_dict() for issue in issues],
            "visualization": visualization,
        }

    def _resolve_exercise_type(self, exercise_type: str | None) -> str:
        normalized = (exercise_type or "squat").strip().lower()
        if normalized != "squat":
            raise ValueError(f"Unsupported exercise_type '{exercise_type}'. Only 'squat' is currently implemented.")
        return normalized

    def _build_summary(
        self,
        frames_raw: list[dict],
        clean_frames: list,
        video_info: dict,
        exercise_type: str | None,
        rep_count: int,
        bodyweight_kg: float | None,
        external_load_kg: float | None,
        bar_placement_mode: str,
        bar_placement_resolved: str,
    ) -> dict:
        duration_ms = float(frames_raw[-1].get("timestampMs") or 0.0) if frames_raw else 0.0
        source_fps = float(video_info.get("sourceFps") or 0.0)
        frame_count = len(frames_raw)
        sampled_fps = (
            frame_count / max(duration_ms / 1000.0, 1.0)
            if frame_count
            else float(video_info.get("effectiveSamplingFps") or 0.0)
        )
        usable_frame_count = sum(1 for frame in clean_frames if frame.is_usable)
        detected_frame_count = sum(1 for frame in clean_frames if frame.pose_detected)
        detection_ratio = detected_frame_count / max(frame_count, 1)

        return {
            "exerciseType": exercise_type,
            "repCount": rep_count,
            "frameCount": frame_count,
            "durationMs": round(duration_ms, 6),
            "sourceFps": round(source_fps, 6),
            "sampledFps": round(sampled_fps, 6),
            "detectionRatio": round(detection_ratio, 6),
            "usableFrameCount": usable_frame_count,
            "bodyweightKg": bodyweight_kg,
            "externalLoadKg": external_load_kg,
            "barPlacementMode": bar_placement_mode,
            "barPlacementResolved": bar_placement_resolved,
            "totalSystemMassKg": (
                round((bodyweight_kg or 0.0) + (external_load_kg or 0.0), 6)
                if bodyweight_kg is not None or external_load_kg is not None
                else None
            ),
        }
