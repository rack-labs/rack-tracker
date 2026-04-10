from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from service.analysis_body_profile import BodyProfile
from service.analysis_cop import GroundRef
from service.analysis_kpis import KPI
from service.analysis_reps import RepSegment
from service.analysis_thresholds import PersonalThresholds


@dataclass(slots=True)
class Issue:
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    timestamp_ms: float | None
    rep_index: int | None
    context: dict

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "timestampMs": None if self.timestamp_ms is None else round(self.timestamp_ms, 6),
            "repIndex": self.rep_index,
            "context": self.context,
        }


def detect_issues(
    rep_segments: list[RepSegment],
    kpis: list[KPI],
    body_profile: BodyProfile,
    ground_ref: GroundRef,
    summary: dict,
    thresholds: PersonalThresholds,
) -> list[Issue]:
    issues: list[Issue] = []
    kpi_map = {kpi.key: kpi.value for kpi in kpis}
    detection_ratio = float(summary.get("detectionRatio") or 0.0)

    if not rep_segments:
        issues.append(Issue("error", "no_reps_detected", "No rep segment was detected.", None, None, {}))
    if detection_ratio < 0.8:
        issues.append(Issue("error", "low_detection_ratio", "Pose detection ratio is too low for reliable analysis.", None, None, {"detectionRatio": round(detection_ratio, 6)}))
    if kpi_map.get("trunk_lean_excess", 0.0) > thresholds.trunk_lean_excess_deg:
        issues.append(Issue("warning", "excessive_trunk_lean", "Average trunk lean exceeds the personal reference baseline.", None, None, {"trunkLeanExcessDeg": round(kpi_map.get("trunk_lean_excess", 0.0), 6), "thresholdDeg": round(thresholds.trunk_lean_excess_deg, 6)}))
    if kpi_map.get("avg_load_ratio_knee", 0.0) > thresholds.load_imbalance_warn:
        issues.append(Issue("warning", "movement_load_imbalance", "Left-right loading imbalance exceeds the personalized warning threshold.", None, None, {"avgLoadRatioKnee": round(kpi_map.get("avg_load_ratio_knee", 0.0), 6), "threshold": round(thresholds.load_imbalance_warn, 6), "structuralAsymmetryBaseline": round(body_profile.limb_asymmetry.get("femur", 0.0), 6)}))
    if kpi_map.get("avg_depth_angle", 0.0) > thresholds.depth_angle_upper_deg:
        issues.append(Issue("warning", "insufficient_depth", "Average squat depth is shallower than the personal target range.", None, None, {"avgDepthAngle": round(kpi_map.get("avg_depth_angle", 0.0), 6), "thresholdDeg": round(thresholds.depth_angle_upper_deg, 6)}))
    if kpi_map.get("depth_consistency", 1.0) < thresholds.depth_consistency_min:
        issues.append(Issue("warning", "depth_inconsistency", "Rep depth is not consistent enough across the session.", None, None, {"depthConsistency": round(kpi_map.get("depth_consistency", 0.0), 6), "threshold": round(thresholds.depth_consistency_min, 6)}))
    if kpi_map.get("tempo_consistency", 1.0) < 0.75:
        issues.append(Issue("info", "tempo_inconsistency", "Rep tempo varies noticeably across the session.", None, None, {"tempoConsistency": round(kpi_map.get("tempo_consistency", 0.0), 6)}))

    for rep in rep_segments:
        if (rep.end_ms - rep.start_ms) < 1000.0:
            issues.append(Issue("info", "short_rep_duration", "A rep duration is shorter than 1000 ms.", rep.start_ms, rep.rep_index, {"repDurationMs": round(rep.end_ms - rep.start_ms, 6)}))

    if any(value > 0.03 for value in body_profile.limb_asymmetry.values()):
        issues.append(Issue("info", "structural_asymmetry_noted", "A structural asymmetry baseline was noted and recorded for interpretation.", None, None, {key: round(value, 6) for key, value in body_profile.limb_asymmetry.items()}))

    if thresholds.cop_enabled and ground_ref.view_type == "sagittal":
        if kpi_map.get("cop_bottom_ap", 0.0) > thresholds.cop_ap_forward_warn:
            issues.append(Issue("warning", "cop_anterior_overload", "Bottom-position CoP is shifted too far forward.", None, None, {"copBottomAp": round(kpi_map.get("cop_bottom_ap", 0.0), 6), "threshold": round(thresholds.cop_ap_forward_warn, 6)}))
        if kpi_map.get("cop_bottom_ap", 0.0) < thresholds.cop_ap_backward_warn:
            issues.append(Issue("warning", "cop_posterior_instability", "Bottom-position CoP is shifted too far backward.", None, None, {"copBottomAp": round(kpi_map.get("cop_bottom_ap", 0.0), 6), "threshold": round(thresholds.cop_ap_backward_warn, 6)}))
        if kpi_map.get("cop_ap_consistency", 1.0) < thresholds.cop_consistency_min:
            issues.append(Issue("warning", "cop_instability", "Anterior-posterior CoP is not stable enough across reps.", None, None, {"copApConsistency": round(kpi_map.get("cop_ap_consistency", 0.0), 6), "threshold": round(thresholds.cop_consistency_min, 6)}))
    elif thresholds.cop_enabled and ground_ref.view_type == "frontal":
        if abs(kpi_map.get("cop_bottom_ml", 0.0)) > thresholds.cop_ml_asymmetry_warn:
            issues.append(Issue("warning", "cop_lateral_asymmetry", "Bottom-position CoP shows excessive side-to-side asymmetry.", None, None, {"copBottomMl": round(kpi_map.get("cop_bottom_ml", 0.0), 6), "threshold": round(thresholds.cop_ml_asymmetry_warn, 6)}))
        if kpi_map.get("cop_ml_consistency", 1.0) < thresholds.cop_consistency_min:
            issues.append(Issue("warning", "cop_instability", "Medial-lateral CoP is not stable enough across reps.", None, None, {"copMlConsistency": round(kpi_map.get("cop_ml_consistency", 0.0), 6), "threshold": round(thresholds.cop_consistency_min, 6)}))
    else:
        issues.append(Issue("info", "cop_analysis_unavailable", "CoP analysis is unavailable because view inference is not reliable enough.", None, None, {"viewType": ground_ref.view_type, "viewConfidence": round(ground_ref.view_confidence, 6), "thresholdMode": thresholds.cop_reason}))

    ratio = kpi_map.get("knee_hip_moment_ratio", 0.0)
    if ratio > 1.5:
        issues.append(Issue("info", "knee_dominant_loading", "Bottom mechanics appear knee-dominant.", None, None, {}))
    if ratio and ratio < 0.5:
        issues.append(Issue("info", "hip_dominant_loading", "Bottom mechanics appear hip-dominant.", None, None, {}))
    if kpi_map.get("bar_midfoot_offset", 0.0) > thresholds.bar_midfoot_offset_warn:
        issues.append(Issue("warning", "bar_forward_of_midfoot", "Estimated bar path stays too far forward of midfoot.", None, None, {"barMidfootOffset": round(kpi_map.get("bar_midfoot_offset", 0.0), 6), "threshold": round(thresholds.bar_midfoot_offset_warn, 6)}))
    return issues
