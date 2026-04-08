from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Literal

from service.analysis_body_profile import BodyProfile, calc_angle, midpoint, point
from service.analysis_preprocess import FrameData, JointData

BarPlacementMode = Literal["auto", "high_bar", "low_bar"]
BODY_COM_SEGMENTS = (
    ("mid_ear", "nose", 0.58, 0.081),
    ("hip_center", "shoulder_center", 0.44, 0.424),
    ("left_shoulder", "left_wrist", 0.5, 0.05),
    ("right_shoulder", "right_wrist", 0.5, 0.05),
    ("left_hip", "left_knee", 0.433, 0.1),
    ("right_hip", "right_knee", 0.433, 0.1),
    ("left_knee", "left_ankle", 0.433, 0.0465),
    ("right_knee", "right_ankle", 0.433, 0.0465),
    ("left_ankle", "left_foot_index", 0.5, 0.0145),
    ("right_ankle", "right_foot_index", 0.5, 0.0145),
)


@dataclass(slots=True)
class FeatureSet:
    timestamps_ms: list[float]
    joint_angles: dict[str, list[float]]
    joint_velocities: dict[str, list[float]]
    hip_heights: list[float]
    bar_path_x: list[float]
    load_ratios: dict[str, list[float]]
    bar_placement_input: str = "auto"
    bar_placement_resolved: str = "auto"
    body_com_x: list[float] = field(default_factory=list)
    body_com_y: list[float] = field(default_factory=list)
    com_x: list[float] = field(default_factory=list)
    com_y: list[float] = field(default_factory=list)
    cop_ap_normalized: list[float | None] = field(default_factory=list)
    cop_ml_normalized: list[float | None] = field(default_factory=list)
    moment_arms: dict[str, list[float | None]] = field(default_factory=dict)
    bar_over_midfoot: list[float | None] = field(default_factory=list)
    bar_y: list[float] = field(default_factory=list)
    bar_confidence: list[float] = field(default_factory=list)
    bar_com_offset: list[float | None] = field(default_factory=list)

    def to_timeseries_dict(self) -> dict:
        result = {
            "timestamps_ms": _rounded_list(self.timestamps_ms),
            "bar_placement_input": self.bar_placement_input,
            "bar_placement_resolved": self.bar_placement_resolved,
            "hip_height": _rounded_list(self.hip_heights),
            "bar_x": _rounded_list(self.bar_path_x),
            "bar_y": _rounded_list(self.bar_y),
            "bar_confidence": _rounded_list(self.bar_confidence),
            "bar_com_offset": _rounded_optional_list(self.bar_com_offset),
            "body_com_x": _rounded_list(self.body_com_x),
            "body_com_y": _rounded_list(self.body_com_y),
            "com_x": _rounded_list(self.com_x),
            "com_y": _rounded_list(self.com_y),
            "cop_ap_normalized": _rounded_optional_list(self.cop_ap_normalized),
            "cop_ml_normalized": _rounded_optional_list(self.cop_ml_normalized),
            "bar_over_midfoot": _rounded_optional_list(self.bar_over_midfoot),
        }
        for key, values in self.joint_angles.items():
            result[key] = _rounded_list(values)
        for key, values in self.joint_velocities.items():
            result[key] = _rounded_list(values)
        for key, values in self.load_ratios.items():
            result[key] = _rounded_list(values)
        for key, values in self.moment_arms.items():
            result[f"moment_arm_{key}"] = _rounded_optional_list(values)
        return result


def extract_features(
    frames: list[FrameData],
    body_profile: BodyProfile,
    bar_placement_mode: BarPlacementMode = "auto",
) -> FeatureSet:
    usable_frames = [frame for frame in frames if frame.is_usable]
    timestamps = [frame.timestamp_ms for frame in usable_frames]
    left_knee_angles: list[float] = []
    right_knee_angles: list[float] = []
    left_hip_angles: list[float] = []
    right_hip_angles: list[float] = []
    trunk_lean_angles: list[float] = []
    hip_heights: list[float] = []
    bar_path_x: list[float] = []
    bar_y: list[float] = []
    bar_confidence: list[float] = []
    com_x: list[float] = []
    com_y: list[float] = []
    body_com_x: list[float] = []
    body_com_y: list[float] = []
    load_ratio_knee: list[float] = []
    resolved_modes: list[str] = []

    for frame in usable_frames:
        left_knee = calc_angle(point(frame.joints["left_hip"]), point(frame.joints["left_knee"]), point(frame.joints["left_ankle"]))
        right_knee = calc_angle(point(frame.joints["right_hip"]), point(frame.joints["right_knee"]), point(frame.joints["right_ankle"]))
        left_hip = calc_angle(point(frame.joints["left_shoulder"]), point(frame.joints["left_hip"]), point(frame.joints["left_knee"]))
        right_hip = calc_angle(point(frame.joints["right_shoulder"]), point(frame.joints["right_hip"]), point(frame.joints["right_knee"]))
        shoulder_center = midpoint(frame.joints["left_shoulder"], frame.joints["right_shoulder"])
        hip_center = midpoint(frame.joints["left_hip"], frame.joints["right_hip"])
        bar_x, bar_center_y, bar_estimation_confidence, resolved_mode = _estimate_barbell_proxy(
            frame,
            shoulder_center,
            hip_center,
            bar_placement_mode=bar_placement_mode,
        )
        trunk_lean = _trunk_lean_angle(shoulder_center, hip_center)

        left_knee_angles.append(left_knee)
        right_knee_angles.append(right_knee)
        left_hip_angles.append(left_hip)
        right_hip_angles.append(right_hip)
        trunk_lean_angles.append(trunk_lean)
        hip_heights.append(hip_center[1])
        bar_path_x.append(bar_x)
        bar_y.append(bar_center_y)
        bar_confidence.append(bar_estimation_confidence)
        resolved_modes.append(resolved_mode)
        body_x, body_y = _estimate_body_com(frame, shoulder_center, hip_center)
        body_com_x.append(body_x)
        body_com_y.append(body_y)
        com_x.append(body_x)
        com_y.append(body_y)
        load_ratio_knee.append(max(0.0, abs(left_knee - right_knee) - body_profile.joint_angle_baseline_deg.get("knee", 0.0)) / 180.0)

    return FeatureSet(
        timestamps_ms=timestamps,
        joint_angles={
            "left_knee_angle": left_knee_angles,
            "right_knee_angle": right_knee_angles,
            "left_hip_angle": left_hip_angles,
            "right_hip_angle": right_hip_angles,
            "trunk_lean_angle": trunk_lean_angles,
        },
        joint_velocities={
            "left_knee_angle_velocity": _central_velocity(timestamps, left_knee_angles),
            "right_knee_angle_velocity": _central_velocity(timestamps, right_knee_angles),
            "hip_height_velocity": _central_velocity(timestamps, hip_heights),
        },
        hip_heights=hip_heights,
        bar_path_x=bar_path_x,
        load_ratios={"load_ratio_knee": load_ratio_knee},
        bar_placement_input=bar_placement_mode,
        bar_placement_resolved=_resolve_session_bar_mode(bar_placement_mode, resolved_modes),
        body_com_x=body_com_x,
        body_com_y=body_com_y,
        com_x=com_x,
        com_y=com_y,
        moment_arms={
            "left_ankle": [None] * len(timestamps),
            "right_ankle": [None] * len(timestamps),
            "left_knee": [None] * len(timestamps),
            "right_knee": [None] * len(timestamps),
            "left_hip": [None] * len(timestamps),
            "right_hip": [None] * len(timestamps),
        },
        bar_over_midfoot=[None] * len(timestamps),
        bar_y=bar_y,
        bar_confidence=bar_confidence,
        bar_com_offset=[bar_path_x[idx] - com_x[idx] for idx in range(len(bar_path_x))],
    )


def _trunk_lean_angle(shoulder_center: tuple[float, float], hip_center: tuple[float, float]) -> float:
    vertical_anchor = (hip_center[0], hip_center[1] - 1.0)
    return calc_angle(shoulder_center, hip_center, vertical_anchor)


def _estimate_barbell_proxy(
    frame: FrameData,
    shoulder_center: tuple[float, float],
    hip_center: tuple[float, float],
    bar_placement_mode: BarPlacementMode,
) -> tuple[float, float, float, str]:
    left_shoulder = frame.joints["left_shoulder"]
    right_shoulder = frame.joints["right_shoulder"]
    left_elbow, left_elbow_penalty = _joint_or_fallback(frame, "left_elbow", left_shoulder)
    right_elbow, right_elbow_penalty = _joint_or_fallback(frame, "right_elbow", right_shoulder)
    left_wrist, left_wrist_penalty = _joint_or_fallback(frame, "left_wrist", left_elbow)
    right_wrist, right_wrist_penalty = _joint_or_fallback(frame, "right_wrist", right_elbow)

    shoulder_width = abs(left_shoulder.x - right_shoulder.x)
    elbow_center = midpoint(left_elbow, right_elbow)
    wrist_center = midpoint(left_wrist, right_wrist)
    torso_height = max(abs(hip_center[1] - shoulder_center[1]), 1e-6)

    shoulder_conf = mean([left_shoulder.visibility, right_shoulder.visibility])
    elbow_conf = mean([left_elbow.visibility, right_elbow.visibility])
    wrist_conf = mean([left_wrist.visibility, right_wrist.visibility])

    if bar_placement_mode == "high_bar":
        x_weights = (0.84, 0.12, 0.04)
        y_offset_factor = 0.06
        max_offset_factor = 0.22
        resolved_mode = "high_bar"
    elif bar_placement_mode == "low_bar":
        x_weights = (0.62, 0.26, 0.12)
        y_offset_factor = -0.02
        max_offset_factor = 0.38
        resolved_mode = "low_bar"
    else:
        x_weights, y_offset_factor, max_offset_factor, resolved_mode = _auto_bar_placement_params(
            shoulder_center=shoulder_center,
            elbow_center=elbow_center,
            wrist_center=wrist_center,
            shoulder_width=shoulder_width,
            torso_height=torso_height,
        )

    raw_bar_x = (
        (shoulder_center[0] * x_weights[0])
        + (elbow_center[0] * x_weights[1])
        + (wrist_center[0] * x_weights[2])
    )
    max_offset = shoulder_width * max_offset_factor
    bar_x = shoulder_center[0] + max(-max_offset, min(max_offset, raw_bar_x - shoulder_center[0]))
    bar_y = shoulder_center[1] - (torso_height * y_offset_factor)
    confidence = min(0.99, (shoulder_conf * 0.6) + (elbow_conf * 0.25) + (wrist_conf * 0.15))
    confidence = max(
        0.0,
        confidence - left_elbow_penalty - right_elbow_penalty - left_wrist_penalty - right_wrist_penalty,
    )
    return bar_x, bar_y, confidence, resolved_mode


def _auto_bar_placement_params(
    shoulder_center: tuple[float, float],
    elbow_center: tuple[float, float],
    wrist_center: tuple[float, float],
    shoulder_width: float,
    torso_height: float,
) -> tuple[tuple[float, float, float], float, float, str]:
    # Fallback to high_bar when geometry is degenerate.
    if shoulder_width <= 1e-6:
        return (0.84, 0.12, 0.04), 0.06, 0.22, "high_bar"

    # --- Signal 1: arm forward bias (X axis) ---
    # low_bar → elbows/wrists pulled forward relative to shoulder center
    arm_forward_bias = ((elbow_center[0] - shoulder_center[0]) * 0.6) + (
        (wrist_center[0] - shoulder_center[0]) * 0.4
    )
    normalized_x_bias = arm_forward_bias / shoulder_width
    # Map [0.08, 0.20] → [0, 1]  (0 = high_bar, 1 = low_bar)
    x_score = max(0.0, min(1.0, (normalized_x_bias - 0.08) / 0.12))

    # --- Signal 2: elbow vertical drop (Y axis, image-down is positive) ---
    # high_bar → elbows near or above shoulder level (small positive / negative drop)
    # low_bar  → elbows drop below shoulder (larger positive drop)
    elbow_y_drop = (elbow_center[1] - shoulder_center[1]) / max(torso_height, 1e-6)
    # Map [0.0, 0.20] → [0, 1]
    y_score = max(0.0, min(1.0, elbow_y_drop / 0.20))

    # --- Combine: X is the stronger signal for sagittal view ---
    t = x_score * 0.6 + y_score * 0.4  # 0.0 = high_bar, 1.0 = low_bar

    # --- Interpolate params continuously ---
    def _lerp(hi: float, lo: float) -> float:
        return hi + (lo - hi) * t

    x_weights = (_lerp(0.84, 0.62), _lerp(0.12, 0.26), _lerp(0.04, 0.12))
    y_offset_factor = _lerp(0.06, -0.02)
    max_offset_factor = _lerp(0.22, 0.38)

    # --- Derive display label from continuous score ---
    if t < 0.35:
        label = "high_bar"
    elif t > 0.65:
        label = "low_bar"
    else:
        label = "auto"

    return x_weights, y_offset_factor, max_offset_factor, label


def _resolve_session_bar_mode(input_mode: str, resolved_modes: list[str]) -> str:
    if input_mode != "auto":
        return input_mode
    if not resolved_modes:
        return "high_bar"
    high_count = sum(1 for mode in resolved_modes if mode == "high_bar")
    low_count = sum(1 for mode in resolved_modes if mode == "low_bar")
    if low_count > high_count:
        return "low_bar"
    return "high_bar"


def _central_velocity(timestamps_ms: list[float], values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [0.0]
    velocity = [0.0] * len(values)
    for idx in range(len(values)):
        if idx == 0:
            dt = max((timestamps_ms[1] - timestamps_ms[0]) / 1000.0, 1e-6)
            velocity[idx] = (values[1] - values[0]) / dt
            continue
        if idx == len(values) - 1:
            dt = max((timestamps_ms[-1] - timestamps_ms[-2]) / 1000.0, 1e-6)
            velocity[idx] = (values[-1] - values[-2]) / dt
            continue
        dt = max((timestamps_ms[idx + 1] - timestamps_ms[idx - 1]) / 2000.0, 1e-6)
        velocity[idx] = (values[idx + 1] - values[idx - 1]) / dt
    return velocity


def _rounded_list(values: list[float]) -> list[float]:
    return [round(value, 6) for value in values]


def _rounded_optional_list(values: list[float | None]) -> list[float | None]:
    return [None if value is None else round(value, 6) for value in values]


def _estimate_body_com(
    frame: FrameData,
    shoulder_center: tuple[float, float],
    hip_center: tuple[float, float],
) -> tuple[float, float]:
    virtual_points = {
        "mid_ear": _midpoint_tuple(_joint_point(frame, "left_ear"), _joint_point(frame, "right_ear")),
        "nose": _joint_point(frame, "nose"),
        "hip_center": hip_center,
        "shoulder_center": shoulder_center,
        "left_shoulder": _joint_point(frame, "left_shoulder"),
        "right_shoulder": _joint_point(frame, "right_shoulder"),
        "left_wrist": _joint_or_virtual(frame, "left_wrist", "left_elbow", shoulder_center),
        "right_wrist": _joint_or_virtual(frame, "right_wrist", "right_elbow", shoulder_center),
        "left_hip": _joint_point(frame, "left_hip"),
        "right_hip": _joint_point(frame, "right_hip"),
        "left_knee": _joint_point(frame, "left_knee"),
        "right_knee": _joint_point(frame, "right_knee"),
        "left_ankle": _joint_point(frame, "left_ankle"),
        "right_ankle": _joint_point(frame, "right_ankle"),
        "left_foot_index": _joint_or_virtual(frame, "left_foot_index", "left_ankle", hip_center),
        "right_foot_index": _joint_or_virtual(frame, "right_foot_index", "right_ankle", hip_center),
    }

    total_x = 0.0
    total_y = 0.0
    total_mass = 0.0
    for prox_name, dist_name, com_frac, mass_frac in BODY_COM_SEGMENTS:
        prox = virtual_points.get(prox_name)
        dist = virtual_points.get(dist_name)
        if prox is None or dist is None:
            continue
        seg_x = prox[0] + (dist[0] - prox[0]) * com_frac
        seg_y = prox[1] + (dist[1] - prox[1]) * com_frac
        total_x += seg_x * mass_frac
        total_y += seg_y * mass_frac
        total_mass += mass_frac

    if total_mass <= 1e-6:
        return (
            (shoulder_center[0] * 0.35) + (hip_center[0] * 0.65),
            (shoulder_center[1] * 0.35) + (hip_center[1] * 0.65),
        )
    return total_x / total_mass, total_y / total_mass


def _joint_or_fallback(
    frame: FrameData,
    joint_name: str,
    fallback: JointData,
) -> tuple[JointData, float]:
    joint = frame.joints.get(joint_name)
    if joint is None:
        return fallback, 0.25
    if not joint.is_reliable:
        return joint, 0.15
    return joint, 0.0


def _joint_point(frame: FrameData, joint_name: str) -> tuple[float, float] | None:
    joint = frame.joints.get(joint_name)
    if joint is None:
        return None
    return (joint.x, joint.y)


def _joint_or_virtual(
    frame: FrameData,
    joint_name: str,
    fallback_name: str,
    anchor: tuple[float, float],
) -> tuple[float, float] | None:
    point = _joint_point(frame, joint_name)
    if point is not None:
        return point
    fallback = _joint_point(frame, fallback_name)
    return fallback if fallback is not None else anchor


def _midpoint_tuple(
    left: tuple[float, float] | None,
    right: tuple[float, float] | None,
) -> tuple[float, float] | None:
    if left is not None and right is not None:
        return ((left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0)
    return left or right
