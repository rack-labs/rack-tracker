from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from service.analysis_body_profile import BodyProfile
from service.analysis_cop import GroundRef
from service.analysis_reps import RepSegment


@dataclass(slots=True)
class TrunkLeanBaseline:
    expected_trunk_lean_deg: float
    trunk_lean_excess_deg: float
    context: str


@dataclass(slots=True)
class PersonalThresholds:
    trunk_lean_excess_deg: float
    load_imbalance_warn: float
    depth_angle_upper_deg: float
    depth_consistency_min: float
    cop_ap_forward_warn: float
    cop_ap_backward_warn: float
    cop_ml_asymmetry_warn: float
    cop_ap_range: float
    cop_ml_range: float
    cop_consistency_min: float
    bar_midfoot_offset_warn: float
    cop_enabled: bool
    cop_reason: str


def build_trunk_lean_baseline(
    body_profile: BodyProfile,
    rep_segments: list[RepSegment],
) -> TrunkLeanBaseline:
    depth_values = [rep.depth_angle_deg for rep in rep_segments]
    avg_depth_angle = mean(depth_values) if depth_values else 110.0
    normalized_depth = _clamp((110.0 - avg_depth_angle) / 35.0, 0.0, 1.0)
    femur_ratio_delta = body_profile.femur_to_torso_ratio - 0.78
    tibia_ratio_delta = body_profile.tibia_to_femur_ratio - 0.85

    expected = _clamp(
        17.0 + _clamp((femur_ratio_delta * 28.0) + (tibia_ratio_delta * 8.0), -4.0, 10.0) + (normalized_depth * 8.0),
        8.0,
        40.0,
    )
    excess_threshold = _clamp(
        8.0 + max(0.0, femur_ratio_delta) * 8.0 + (normalized_depth * 1.5),
        6.5,
        12.5,
    )
    context = (
        f"referenceBaseline=ratio+depth;"
        f" femurToTorsoRatio={body_profile.femur_to_torso_ratio:.3f};"
        f" tibiaToFemurRatio={body_profile.tibia_to_femur_ratio:.3f};"
        f" avgDepthAngle={avg_depth_angle:.1f};"
        f" normalizedDepth={normalized_depth:.3f};"
        f" excessWarnDeg={excess_threshold:.2f};"
        f" note=working baseline, not a calibrated biomechanical model"
    )
    return TrunkLeanBaseline(expected, excess_threshold, context)


def build_personal_thresholds(
    body_profile: BodyProfile,
    rep_segments: list[RepSegment],
    kpi_map: dict[str, float],
    ground_ref: GroundRef,
) -> PersonalThresholds:
    baseline = build_trunk_lean_baseline(body_profile, rep_segments)
    rep_count = len(rep_segments)
    max_limb_asymmetry = max(body_profile.limb_asymmetry.values(), default=0.0)
    avg_depth_angle = kpi_map.get("avg_depth_angle", mean([rep.depth_angle_deg for rep in rep_segments]) if rep_segments else 0.0)
    session_deep_bias = _clamp((100.0 - avg_depth_angle) / 20.0, 0.0, 1.0)

    load_imbalance_warn = _clamp(
        0.08 + (max_limb_asymmetry * 0.6) + (body_profile.joint_angle_baseline_deg.get("knee", 0.0) * 0.0015),
        0.08,
        0.14,
    )
    depth_angle_upper_deg = _clamp(
        104.0
        + max(0.0, body_profile.femur_to_torso_ratio - 0.78) * 10.0
        - max(0.0, body_profile.tibia_to_femur_ratio - 0.85) * 4.0
        - (session_deep_bias * 2.0),
        99.0,
        108.0,
    )
    depth_consistency_min = 0.84 if rep_count >= 4 else 0.82 if rep_count >= 2 else 0.78

    cop_enabled = ground_ref.view_type in {"sagittal", "frontal"} and ground_ref.view_confidence >= 0.7
    cop_ap_range, cop_ml_range = build_cop_consistency_ranges(body_profile, ground_ref)
    if not cop_enabled:
        cop_reason = "disabled_low_view_confidence"
        cop_ap_forward_warn = 1.0
        cop_ap_backward_warn = -1.0
        cop_ml_asymmetry_warn = 1.0
        cop_consistency_min = 0.0
    else:
        relaxed = ground_ref.view_confidence < 0.82
        bar_mode = ground_ref.bar_placement_resolved or "auto"
        load_bias = 0.0
        if ground_ref.bodyweight_kg and ground_ref.external_load_kg:
            relative_load = ground_ref.external_load_kg / max(ground_ref.bodyweight_kg, 1e-6)
            load_bias = _clamp(relative_load - 1.0, 0.0, 1.0) * 0.02

        forward_base = 0.25
        if bar_mode == "high_bar":
            forward_base += 0.02
        elif bar_mode == "low_bar":
            forward_base -= 0.02

        cop_reason = "relaxed_view_confidence" if relaxed else "enabled"
        relax_delta = 0.04 if relaxed else 0.0
        cop_ap_forward_warn = forward_base + load_bias + relax_delta
        cop_ap_backward_warn = -0.18 - (0.02 if relaxed else 0.0)
        cop_ml_asymmetry_warn = _clamp(0.18 + (max_limb_asymmetry * 0.5) + relax_delta, 0.18, 0.28)
        cop_consistency_min = 0.62 if relaxed else 0.72

    bar_midfoot_offset_warn = _clamp(
        0.05
        + (0.008 if ground_ref.bar_placement_resolved == "high_bar" else 0.0)
        + (0.005 if ground_ref.view_confidence < 0.7 else 0.0),
        0.045,
        0.07,
    )

    return PersonalThresholds(
        trunk_lean_excess_deg=baseline.trunk_lean_excess_deg,
        load_imbalance_warn=load_imbalance_warn,
        depth_angle_upper_deg=depth_angle_upper_deg,
        depth_consistency_min=depth_consistency_min,
        cop_ap_forward_warn=cop_ap_forward_warn,
        cop_ap_backward_warn=cop_ap_backward_warn,
        cop_ml_asymmetry_warn=cop_ml_asymmetry_warn,
        cop_ap_range=cop_ap_range,
        cop_ml_range=cop_ml_range,
        cop_consistency_min=cop_consistency_min,
        bar_midfoot_offset_warn=bar_midfoot_offset_warn,
        cop_enabled=cop_enabled,
        cop_reason=cop_reason,
    )


def build_cop_consistency_ranges(
    body_profile: BodyProfile,
    ground_ref: GroundRef,
) -> tuple[float, float]:
    asymmetry = max(body_profile.limb_asymmetry.values(), default=0.0)
    relaxed_delta = 0.04 if ground_ref.view_confidence < 0.82 else 0.0
    ap_range = _clamp(0.22 + asymmetry * 0.35 + relaxed_delta, 0.22, 0.34)
    ml_range = _clamp(0.18 + asymmetry * 0.45 + relaxed_delta, 0.18, 0.3)
    return ap_range, ml_range


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
