from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev

from service.analysis_body_profile import BodyProfile
from service.analysis_cop import GroundRef
from service.analysis_features import FeatureSet
from service.analysis_reps import RepSegment
from service.analysis_thresholds import build_cop_consistency_ranges, build_trunk_lean_baseline


@dataclass(slots=True)
class KPI:
    key: str
    label: str
    value: float
    unit: str
    description: str
    personal_context: str | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "value": round(self.value, 6),
            "unit": self.unit,
            "description": self.description,
            "personalContext": self.personal_context,
        }


def calc_kpis(
    features: FeatureSet,
    rep_segments: list[RepSegment],
    body_profile: BodyProfile,
    ground_ref: GroundRef,
) -> list[KPI]:
    depth_values = [rep.depth_angle_deg for rep in rep_segments]
    rep_durations = [rep.end_ms - rep.start_ms for rep in rep_segments]
    bottom_indices = [_closest_index(features.timestamps_ms, rep.bottom_ms) for rep in rep_segments]
    trunk_lean_values = features.joint_angles.get("trunk_lean_angle", [])
    avg_trunk_lean = mean(trunk_lean_values) if trunk_lean_values else 0.0
    trunk_lean_baseline = build_trunk_lean_baseline(body_profile, rep_segments)
    cop_ap_range, cop_ml_range = build_cop_consistency_ranges(body_profile, ground_ref)
    knee_moment = (
        _mean_optional(
            [
                _mean_optional([features.moment_arms["left_knee"][idx], features.moment_arms["right_knee"][idx]])
                for idx in bottom_indices
            ]
        )
        if bottom_indices
        else 0.0
    )
    hip_moment = (
        _mean_optional(
            [
                _mean_optional([features.moment_arms["left_hip"][idx], features.moment_arms["right_hip"][idx]])
                for idx in bottom_indices
            ]
        )
        if bottom_indices
        else 0.0
    )

    return [
        KPI("rep_count", "Rep Count", float(len(rep_segments)), "reps", "Detected squat repetition count."),
        KPI("avg_depth_angle", "Average Depth Angle", mean(depth_values) if depth_values else 0.0, "deg", "Average bottom knee angle across reps."),
        KPI("depth_consistency", "Depth Consistency", _consistency(depth_values), "ratio", "How consistent rep depth is across the session."),
        KPI("avg_rep_duration_ms", "Average Rep Duration", mean(rep_durations) if rep_durations else 0.0, "ms", "Average duration per repetition."),
        KPI("tempo_consistency", "Tempo Consistency", _consistency(rep_durations), "ratio", "How consistent rep timing is across the session."),
        KPI(
            "avg_eccentric_ratio",
            "Average Eccentric Ratio",
            mean([(rep.bottom_ms - rep.start_ms) / max(rep.end_ms - rep.start_ms, 1e-6) for rep in rep_segments])
            if rep_segments
            else 0.0,
            "ratio",
            "Share of each rep spent in the descent phase.",
        ),
        KPI("avg_trunk_lean", "Average Trunk Lean", avg_trunk_lean, "deg", "Average trunk lean angle across usable frames."),
        KPI(
            "expected_trunk_lean",
            "Expected Trunk Lean",
            trunk_lean_baseline.expected_trunk_lean_deg,
            "deg",
            "Personal reference trunk lean derived from body proportions and session depth.",
            personal_context=trunk_lean_baseline.context,
        ),
        KPI(
            "trunk_lean_excess",
            "Trunk Lean Excess",
            avg_trunk_lean - trunk_lean_baseline.expected_trunk_lean_deg,
            "deg",
            "How far average trunk lean exceeds the personal reference baseline.",
            personal_context=trunk_lean_baseline.context,
        ),
        KPI(
            "avg_load_ratio_knee",
            "Average Knee Load Imbalance",
            mean(features.load_ratios.get("load_ratio_knee", [0.0])) if features.timestamps_ms else 0.0,
            "ratio",
            "Average left-right knee loading asymmetry proxy.",
        ),
        KPI(
            "cop_bottom_ap",
            "Bottom CoP AP",
            _mean_optional([features.cop_ap_normalized[idx] for idx in bottom_indices]) if bottom_indices else 0.0,
            "ratio",
            "Average anterior-posterior CoP position at rep bottom.",
        ),
        KPI(
            "cop_bottom_ml",
            "Bottom CoP ML",
            _mean_optional([features.cop_ml_normalized[idx] for idx in bottom_indices]) if bottom_indices else 0.0,
            "ratio",
            "Average medial-lateral CoP position at rep bottom.",
        ),
        KPI(
            "cop_ap_consistency",
            "CoP AP Consistency",
            _band_consistency(
                [features.cop_ap_normalized[idx] for idx in bottom_indices if features.cop_ap_normalized[idx] is not None],
                cop_ap_range,
            ),
            "ratio",
            "Rep-to-rep consistency of anterior-posterior CoP at the bottom.",
        ),
        KPI(
            "cop_ml_consistency",
            "CoP ML Consistency",
            _band_consistency(
                [features.cop_ml_normalized[idx] for idx in bottom_indices if features.cop_ml_normalized[idx] is not None],
                cop_ml_range,
            ),
            "ratio",
            "Rep-to-rep consistency of medial-lateral CoP at the bottom.",
        ),
        KPI(
            "cop_anterior_shift",
            "CoP Anterior Shift",
            _cop_anterior_shift(features, rep_segments),
            "ratio",
            "Average forward CoP shift from rep start to the deepest point during descent.",
        ),
        KPI("avg_knee_moment_arm", "Average Knee Moment Arm", knee_moment, "normalized", "Average knee moment arm at rep bottom."),
        KPI("avg_hip_moment_arm", "Average Hip Moment Arm", hip_moment, "normalized", "Average hip moment arm at rep bottom."),
        KPI(
            "knee_hip_moment_ratio",
            "Knee to Hip Moment Ratio",
            knee_moment / max(hip_moment, 1e-6) if hip_moment else 0.0,
            "ratio",
            "Bottom-position ratio between knee and hip moment arms.",
        ),
        KPI(
            "bar_midfoot_offset",
            "Bar Midfoot Offset",
            _mean_optional(features.bar_over_midfoot),
            "normalized",
            "Average horizontal offset between estimated bar path and midfoot reference.",
        ),
    ]


def _consistency(values: list[float]) -> float:
    if len(values) <= 1:
        return 1.0 if values else 0.0
    return max(0.0, 1.0 - (pstdev(values) / max(abs(mean(values)), 1e-6)))


def _band_consistency(values: list[float], band: float) -> float:
    if len(values) <= 1:
        return 1.0 if values else 0.0
    return max(0.0, 1.0 - (pstdev(values) / max(band, 1e-6)))


def _cop_anterior_shift(features: FeatureSet, rep_segments: list[RepSegment]) -> float:
    shifts: list[float] = []
    for rep in rep_segments:
        start_idx = _closest_index(features.timestamps_ms, rep.start_ms)
        bottom_idx = _closest_index(features.timestamps_ms, rep.bottom_ms)
        if bottom_idx <= start_idx:
            continue
        start_value = features.cop_ap_normalized[start_idx]
        descent_values = [
            value
            for value in features.cop_ap_normalized[start_idx : bottom_idx + 1]
            if value is not None
        ]
        if start_value is None or not descent_values:
            continue
        shifts.append(max(descent_values) - start_value)
    return mean(shifts) if shifts else 0.0


def _closest_index(values: list[float], target: float) -> int:
    return min(range(len(values)), key=lambda idx: abs(values[idx] - target))


def _mean_optional(values: list[float | None]) -> float:
    filtered = [value for value in values if value is not None]
    return mean(filtered) if filtered else 0.0
