from __future__ import annotations

import json
from statistics import mean
from typing import Any


class LlmPromptPayloadService:
    def build(self, analysis: dict[str, Any]) -> dict[str, Any]:
        summary = analysis.get("summary", {})
        body_profile = analysis.get("bodyProfile", {})
        ground_ref = analysis.get("groundRef", {})
        kpis = analysis.get("kpis", [])
        rep_segments = analysis.get("repSegments", [])
        events = analysis.get("events", [])
        issues = analysis.get("issues", [])
        timeseries = analysis.get("timeseries", {})

        kpi_map = self._build_kpi_map(kpis)

        return {
            "schemaVersion": "v1",
            "exerciseType": str(summary.get("exerciseType") or "unknown"),
            "sessionSummary": {
                "repCount": int(summary.get("repCount") or 0),
                "frameCount": int(summary.get("frameCount") or 0),
                "usableFrameCount": int(summary.get("usableFrameCount") or 0),
                "durationMs": self._round(summary.get("durationMs")),
                "sampledFps": self._round(summary.get("sampledFps")),
                "detectionRatio": self._round(summary.get("detectionRatio")),
                "bodyweightKg": self._round(summary.get("bodyweightKg")),
                "externalLoadKg": self._round(summary.get("externalLoadKg")),
                "totalSystemMassKg": self._round(summary.get("totalSystemMassKg")),
                "barPlacementMode": summary.get("barPlacementMode"),
                "barPlacementResolved": summary.get("barPlacementResolved"),
            },
            "bodyProfile": {
                "femurToTorsoRatio": self._round(body_profile.get("femurToTorsoRatio")),
                "tibiaToFemurRatio": self._round(body_profile.get("tibiaToFemurRatio")),
                "limbAsymmetry": self._round_dict(body_profile.get("limbAsymmetry", {})),
                "jointAngleBaselineDeg": self._round_dict(body_profile.get("jointAngleBaselineDeg", {})),
            },
            "groundContact": {
                "viewType": ground_ref.get("viewType"),
                "viewConfidence": self._round(ground_ref.get("viewConfidence")),
                "midFootX": self._round(ground_ref.get("midFootX")),
                "footWidth": self._round(ground_ref.get("footWidth")),
                "sagittalFootLength": self._round(ground_ref.get("sagittalFootLength")),
                "barPlacementResolved": ground_ref.get("barPlacementResolved"),
            },
            "movementSummary": self._build_movement_summary(timeseries, kpi_map),
            "kpis": self._select_kpis(kpis),
            "repFindings": self._build_rep_findings(rep_segments, timeseries, issues),
            "eventHighlights": self._build_event_highlights(events),
            "issueHighlights": self._build_issue_highlights(issues),
        }

    def estimate_tokens(
        self,
        analysis: dict[str, Any],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        compact_analysis = json.dumps(analysis, ensure_ascii=False, separators=(",", ":"))
        compact_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        analysis_chars = len(compact_analysis)
        payload_chars = len(compact_payload)
        analysis_tokens = self._approx_tokens(compact_analysis)
        payload_tokens = self._approx_tokens(compact_payload)
        saved_tokens = max(analysis_tokens - payload_tokens, 0)
        return {
            "schemaVersion": "v1",
            "source": "coach_prompt_payload",
            "originalAnalysisChars": analysis_chars,
            "originalAnalysisApproxTokens": analysis_tokens,
            "payloadChars": payload_chars,
            "payloadApproxTokens": payload_tokens,
            "savedChars": max(analysis_chars - payload_chars, 0),
            "savedApproxTokens": saved_tokens,
            "reductionRatio": round(saved_tokens / max(analysis_tokens, 1), 4),
            "topLevelKeys": list(payload.keys()),
        }

    def _build_kpi_map(self, kpis: list[dict[str, Any]]) -> dict[str, float]:
        result: dict[str, float] = {}
        for kpi in kpis:
            key = str(kpi.get("key") or "")
            if not key:
                continue
            try:
                result[key] = float(kpi.get("value") or 0.0)
            except (TypeError, ValueError):
                result[key] = 0.0
        return result

    def _select_kpis(self, kpis: list[dict[str, Any]]) -> list[dict[str, Any]]:
        keys = {
            "rep_count",
            "avg_depth_angle",
            "depth_consistency",
            "avg_rep_duration_ms",
            "tempo_consistency",
            "avg_eccentric_ratio",
            "avg_trunk_lean",
            "expected_trunk_lean",
            "trunk_lean_excess",
            "avg_load_ratio_knee",
            "cop_bottom_ap",
            "cop_bottom_ml",
            "cop_ap_consistency",
            "cop_ml_consistency",
            "cop_anterior_shift",
            "avg_knee_moment_arm",
            "avg_hip_moment_arm",
            "knee_hip_moment_ratio",
            "bar_midfoot_offset",
        }
        selected: list[dict[str, Any]] = []
        for kpi in kpis:
            key = str(kpi.get("key") or "")
            if key not in keys:
                continue
            selected.append(
                {
                    "key": key,
                    "label": kpi.get("label"),
                    "value": self._round(kpi.get("value")),
                    "unit": kpi.get("unit"),
                    "description": kpi.get("description"),
                    "personalContext": kpi.get("personalContext"),
                }
            )
        return selected

    def _build_movement_summary(
        self,
        timeseries: dict[str, Any],
        kpi_map: dict[str, float],
    ) -> dict[str, Any]:
        trunk_lean = self._float_list(timeseries.get("trunk_lean_angle", []))
        left_knee = self._float_list(timeseries.get("left_knee_angle", []))
        right_knee = self._float_list(timeseries.get("right_knee_angle", []))
        hip_velocity = self._float_list(timeseries.get("hip_height_velocity", []))
        bar_offset = self._optional_float_list(timeseries.get("bar_over_midfoot", []))
        cop_ap = self._optional_float_list(timeseries.get("cop_ap_normalized", []))
        cop_ml = self._optional_float_list(timeseries.get("cop_ml_normalized", []))
        load_ratio_knee = self._float_list(timeseries.get("load_ratio_knee", []))

        return {
            "trunkLean": {
                "averageDeg": self._round(self._safe_mean(trunk_lean)),
                "maxDeg": self._round(max(trunk_lean) if trunk_lean else None),
                "expectedDeg": self._round(kpi_map.get("expected_trunk_lean")),
                "excessDeg": self._round(kpi_map.get("trunk_lean_excess")),
            },
            "depth": {
                "averageBottomKneeAngleDeg": self._round(kpi_map.get("avg_depth_angle")),
                "minLeftKneeAngleDeg": self._round(min(left_knee) if left_knee else None),
                "minRightKneeAngleDeg": self._round(min(right_knee) if right_knee else None),
            },
            "tempo": {
                "averageRepDurationMs": self._round(kpi_map.get("avg_rep_duration_ms")),
                "eccentricRatio": self._round(kpi_map.get("avg_eccentric_ratio")),
                "consistency": self._round(kpi_map.get("tempo_consistency")),
                "peakHipHeightVelocity": self._round(max(abs(value) for value in hip_velocity) if hip_velocity else None),
            },
            "balance": {
                "averageKneeLoadAsymmetry": self._round(kpi_map.get("avg_load_ratio_knee")),
                "peakKneeLoadAsymmetry": self._round(max(load_ratio_knee) if load_ratio_knee else None),
                "kneeHipMomentRatio": self._round(kpi_map.get("knee_hip_moment_ratio")),
                "bottomCopAp": self._round(kpi_map.get("cop_bottom_ap")),
                "bottomCopMl": self._round(kpi_map.get("cop_bottom_ml")),
                "peakCopAp": self._round(self._max_abs_optional(cop_ap)),
                "peakCopMl": self._round(self._max_abs_optional(cop_ml)),
            },
            "barPath": {
                "averageMidfootOffset": self._round(kpi_map.get("bar_midfoot_offset")),
                "peakMidfootOffset": self._round(self._max_abs_optional(bar_offset)),
                "anteriorShift": self._round(kpi_map.get("cop_anterior_shift")),
            },
        }

    def _build_rep_findings(
        self,
        rep_segments: list[dict[str, Any]],
        timeseries: dict[str, Any],
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        timestamps = self._float_list(timeseries.get("timestamps_ms", []))
        trunk_lean = self._float_list(timeseries.get("trunk_lean_angle", []))
        left_knee = self._float_list(timeseries.get("left_knee_angle", []))
        right_knee = self._float_list(timeseries.get("right_knee_angle", []))
        left_hip = self._float_list(timeseries.get("left_hip_angle", []))
        right_hip = self._float_list(timeseries.get("right_hip_angle", []))
        hip_velocity = self._float_list(timeseries.get("hip_height_velocity", []))
        bar_offset = self._optional_float_list(timeseries.get("bar_over_midfoot", []))
        cop_ap = self._optional_float_list(timeseries.get("cop_ap_normalized", []))
        cop_ml = self._optional_float_list(timeseries.get("cop_ml_normalized", []))
        load_ratio_knee = self._float_list(timeseries.get("load_ratio_knee", []))

        findings: list[dict[str, Any]] = []
        for rep in rep_segments:
            start_ms = float(rep.get("startMs") or 0.0)
            end_ms = float(rep.get("endMs") or 0.0)
            bottom_ms = float(rep.get("bottomMs") or 0.0)
            rep_index = int(rep.get("repIndex") or 0)
            frame_slice = self._slice_indices(timestamps, start_ms, end_ms)
            if not frame_slice:
                continue
            bottom_idx = self._closest_index(timestamps, bottom_ms)
            rep_issue_codes = [
                str(issue.get("code") or "")
                for issue in issues
                if issue.get("repIndex") == rep_index
            ]
            finding = {
                "repIndex": rep_index,
                "timing": {
                    "startMs": self._round(start_ms),
                    "bottomMs": self._round(bottom_ms),
                    "endMs": self._round(end_ms),
                    "durationMs": self._round(end_ms - start_ms),
                    "eccentricShare": self._round((bottom_ms - start_ms) / max(end_ms - start_ms, 1e-6)),
                },
                "bottomMetrics": {
                    "depthAngleDeg": self._round(rep.get("depthAngleDeg")),
                    "trunkLeanDeg": self._series_value(trunk_lean, bottom_idx),
                    "leftKneeAngleDeg": self._series_value(left_knee, bottom_idx),
                    "rightKneeAngleDeg": self._series_value(right_knee, bottom_idx),
                    "leftHipAngleDeg": self._series_value(left_hip, bottom_idx),
                    "rightHipAngleDeg": self._series_value(right_hip, bottom_idx),
                    "barMidfootOffset": self._series_value(bar_offset, bottom_idx),
                    "copAp": self._series_value(cop_ap, bottom_idx),
                    "copMl": self._series_value(cop_ml, bottom_idx),
                    "loadRatioKnee": self._series_value(load_ratio_knee, bottom_idx),
                },
                "peaks": {
                    "maxTrunkLeanDeg": self._round(max(self._slice_values(trunk_lean, frame_slice)) if trunk_lean else None),
                    "maxBarMidfootOffset": self._round(self._max_abs_optional(self._slice_values(bar_offset, frame_slice))),
                    "maxKneeLoadAsymmetry": self._round(max(self._slice_values(load_ratio_knee, frame_slice)) if load_ratio_knee else None),
                    "peakHipHeightVelocity": self._round(
                        max(abs(value) for value in self._slice_values(hip_velocity, frame_slice))
                        if hip_velocity else None
                    ),
                },
                "issueCodes": rep_issue_codes,
            }
            findings.append(finding)
        return findings

    def _build_event_highlights(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        highlights: list[dict[str, Any]] = []
        for event in events:
            event_type = str(event.get("type") or "")
            if event_type == "rep_start" or event_type == "rep_end":
                continue
            highlights.append(
                {
                    "type": event_type,
                    "timestampMs": self._round(event.get("timestampMs")),
                    "repIndex": event.get("repIndex"),
                    "metadata": event.get("metadata", {}),
                }
            )
        return highlights

    def _build_issue_highlights(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "severity": issue.get("severity"),
                "code": issue.get("code"),
                "message": issue.get("message"),
                "repIndex": issue.get("repIndex"),
                "timestampMs": self._round(issue.get("timestampMs")),
                "context": issue.get("context", {}),
            }
            for issue in issues
        ]

    def _slice_indices(self, timestamps: list[float], start_ms: float, end_ms: float) -> list[int]:
        return [
            idx
            for idx, timestamp in enumerate(timestamps)
            if start_ms <= timestamp <= end_ms
        ]

    def _slice_values(self, values: list[Any], indices: list[int]) -> list[Any]:
        return [values[idx] for idx in indices if 0 <= idx < len(values)]

    def _closest_index(self, values: list[float], target: float) -> int:
        if not values:
            return 0
        return min(range(len(values)), key=lambda idx: abs(values[idx] - target))

    def _series_value(self, values: list[Any], idx: int) -> float | None:
        if not values or idx >= len(values):
            return None
        return self._round(values[idx])

    def _float_list(self, values: list[Any]) -> list[float]:
        result: list[float] = []
        for value in values:
            if value is None:
                continue
            try:
                result.append(float(value))
            except (TypeError, ValueError):
                continue
        return result

    def _optional_float_list(self, values: list[Any]) -> list[float | None]:
        result: list[float | None] = []
        for value in values:
            if value is None:
                result.append(None)
                continue
            try:
                result.append(float(value))
            except (TypeError, ValueError):
                result.append(None)
        return result

    def _max_abs_optional(self, values: list[float | None]) -> float | None:
        filtered = [abs(value) for value in values if value is not None]
        return max(filtered) if filtered else None

    def _safe_mean(self, values: list[float]) -> float | None:
        return mean(values) if values else None

    def _round_dict(self, values: dict[str, Any]) -> dict[str, Any]:
        return {key: self._round(value) for key, value in values.items()}

    def _round(self, value: Any) -> float | int | None | str:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            return round(float(value), 6)
        except (TypeError, ValueError):
            return None

    def _approx_tokens(self, text: str) -> int:
        return max(1, round(len(text) / 4))
