from __future__ import annotations

from service.llm_feedback import LlmFeedbackService
from service.llm_prompt_payload import LlmPromptPayloadService


def test_prompt_payload_omits_raw_timeseries_and_reduces_token_estimate() -> None:
    analysis = _analysis_fixture()
    service = LlmPromptPayloadService()

    payload = service.build(analysis)
    diagnostics = service.estimate_tokens(analysis, payload)

    assert "timeseries" not in payload
    assert diagnostics["payloadApproxTokens"] < diagnostics["originalAnalysisApproxTokens"]
    assert diagnostics["savedApproxTokens"] > 0
    assert payload["repFindings"][0]["bottomMetrics"]["trunkLeanDeg"] == 18.0


def test_llm_feedback_uses_compact_payload_without_breaking_output() -> None:
    analysis = _analysis_fixture()
    feedback_service = LlmFeedbackService()
    payload = feedback_service.build_prompt_payload(analysis)

    feedback = feedback_service.generate(analysis, payload)

    assert feedback["model"] == "rule-based-analysis-grounded"
    assert "2 reps" in feedback["overallComment"]
    assert any("femur-to-torso ratio" in highlight for highlight in feedback["highlights"])


def _analysis_fixture() -> dict:
    timestamps = [float(index * 100) for index in range(120)]
    trunk_lean = [10.0 + float(index % 12) for index in range(120)]
    left_knee = [95.0 - float((index % 20) * 2) for index in range(120)]
    right_knee = [96.0 - float((index % 20) * 2) for index in range(120)]
    left_hip = [104.0 - float((index % 18) * 1.8) for index in range(120)]
    right_hip = [105.0 - float((index % 18) * 1.8) for index in range(120)]
    hip_velocity = [(-0.3 + (index % 7) * 0.1) for index in range(120)]
    bar_over_midfoot = [0.01 + ((index % 6) * 0.01) for index in range(120)]
    cop_ap = [0.01 + ((index % 8) * 0.01) for index in range(120)]
    cop_ml = [(-0.02 + (index % 5) * 0.01) for index in range(120)]
    load_ratio_knee = [0.01 + ((index % 6) * 0.01) for index in range(120)]

    return {
        "summary": {
            "exerciseType": "squat",
            "repCount": 2,
            "frameCount": 120,
            "usableFrameCount": 120,
            "durationMs": 11900.0,
            "sampledFps": 30.0,
            "detectionRatio": 1.0,
            "bodyweightKg": 73.0,
            "externalLoadKg": 120.0,
            "totalSystemMassKg": 193.0,
            "barPlacementMode": "auto",
            "barPlacementResolved": "low_bar",
        },
        "bodyProfile": {
            "femurToTorsoRatio": 0.63,
            "tibiaToFemurRatio": 1.29,
            "limbAsymmetry": {"femur": 0.12},
            "jointAngleBaselineDeg": {"knee": 21.0},
        },
        "groundRef": {
            "viewType": "sagittal",
            "viewConfidence": 0.95,
            "midFootX": 0.42,
            "footWidth": 0.3,
            "sagittalFootLength": 0.08,
            "barPlacementResolved": "low_bar",
        },
        "kpis": [
            {"key": "rep_count", "label": "Rep Count", "value": 2, "unit": "reps", "description": ""},
            {"key": "avg_depth_angle", "label": "Average Depth Angle", "value": 55.0, "unit": "deg", "description": ""},
            {"key": "avg_rep_duration_ms", "label": "Average Rep Duration", "value": 2500.0, "unit": "ms", "description": ""},
            {"key": "tempo_consistency", "label": "Tempo Consistency", "value": 0.95, "unit": "ratio", "description": ""},
            {"key": "avg_eccentric_ratio", "label": "Average Eccentric Ratio", "value": 0.4, "unit": "ratio", "description": ""},
            {"key": "avg_trunk_lean", "label": "Average Trunk Lean", "value": 18.0, "unit": "deg", "description": ""},
            {"key": "expected_trunk_lean", "label": "Expected Trunk Lean", "value": 16.0, "unit": "deg", "description": ""},
            {"key": "trunk_lean_excess", "label": "Trunk Lean Excess", "value": 2.0, "unit": "deg", "description": ""},
            {"key": "avg_load_ratio_knee", "label": "Average Knee Load Imbalance", "value": 0.07, "unit": "ratio", "description": ""},
            {"key": "cop_bottom_ap", "label": "Bottom CoP AP", "value": 0.08, "unit": "ratio", "description": ""},
            {"key": "cop_bottom_ml", "label": "Bottom CoP ML", "value": 0.01, "unit": "ratio", "description": ""},
            {"key": "cop_anterior_shift", "label": "CoP Anterior Shift", "value": 0.04, "unit": "ratio", "description": ""},
            {"key": "cop_ml_consistency", "label": "CoP ML Consistency", "value": 0.92, "unit": "ratio", "description": ""},
            {"key": "knee_hip_moment_ratio", "label": "Knee to Hip Moment Ratio", "value": 1.2, "unit": "ratio", "description": ""},
            {"key": "bar_midfoot_offset", "label": "Bar Midfoot Offset", "value": 0.03, "unit": "normalized", "description": ""},
        ],
        "timeseries": {
            "timestamps_ms": timestamps,
            "trunk_lean_angle": trunk_lean,
            "left_knee_angle": left_knee,
            "right_knee_angle": right_knee,
            "left_hip_angle": left_hip,
            "right_hip_angle": right_hip,
            "hip_height_velocity": hip_velocity,
            "bar_over_midfoot": bar_over_midfoot,
            "cop_ap_normalized": cop_ap,
            "cop_ml_normalized": cop_ml,
            "load_ratio_knee": load_ratio_knee,
        },
        "repSegments": [
            {
                "repIndex": 1,
                "startMs": 0.0,
                "bottomMs": 2000.0,
                "endMs": 4900.0,
                "depthAngleDeg": 55.0,
            },
            {
                "repIndex": 2,
                "startMs": 6000.0,
                "bottomMs": 8300.0,
                "endMs": 11200.0,
                "depthAngleDeg": 56.0,
            },
        ],
        "events": [
            {"type": "rep_start", "timestampMs": 0.0, "repIndex": 1, "metadata": {}},
            {"type": "rep_bottom", "timestampMs": 2000.0, "repIndex": 1, "metadata": {"knee_angle": 55.0}},
            {"type": "pose_lost", "timestampMs": 7350.0, "repIndex": 2, "metadata": {"frameIndex": 73}},
        ],
        "issues": [
            {
                "severity": "warning",
                "code": "bar_forward_of_midfoot",
                "message": "Bar is drifting forward.",
                "timestampMs": 2000.0,
                "repIndex": 1,
                "context": {"barMidfootOffset": 0.04},
            }
        ],
    }
