from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Literal

from service.analysis_features import FeatureSet
from service.analysis_preprocess import FrameData


@dataclass(slots=True)
class ViewInference:
    view_type: Literal["sagittal", "frontal", "unknown"]
    confidence: float
    signals: dict[str, float]


@dataclass(slots=True)
class GroundRef:
    ground_y: float
    mid_foot_x: float
    foot_width: float
    sagittal_foot_length: float | None
    left_foot_vec: tuple[float, float]
    right_foot_vec: tuple[float, float]
    sample_frame_count: int
    view_type: Literal["sagittal", "frontal", "unknown"]
    view_confidence: float
    view_signals: dict[str, float]
    bar_placement_input: str
    bar_placement_resolved: str
    bodyweight_kg: float | None
    external_load_kg: float | None
    total_system_mass_kg: float | None

    def to_dict(self) -> dict:
        return {
            "groundY": round(self.ground_y, 6),
            "midFootX": round(self.mid_foot_x, 6),
            "footWidth": round(self.foot_width, 6),
            "sagittalFootLength": None if self.sagittal_foot_length is None else round(self.sagittal_foot_length, 6),
            "leftFootVec": [round(self.left_foot_vec[0], 6), round(self.left_foot_vec[1], 6)],
            "rightFootVec": [round(self.right_foot_vec[0], 6), round(self.right_foot_vec[1], 6)],
            "sampleFrameCount": self.sample_frame_count,
            "viewType": self.view_type,
            "viewConfidence": round(self.view_confidence, 6),
            "viewSignals": {key: round(value, 6) for key, value in self.view_signals.items()},
            "barPlacementInput": self.bar_placement_input,
            "barPlacementResolved": self.bar_placement_resolved,
            "bodyweightKg": self.bodyweight_kg,
            "externalLoadKg": self.external_load_kg,
            "totalSystemMassKg": self.total_system_mass_kg,
        }


def detect_view(frames: list[FrameData]) -> ViewInference:
    usable_frames = [frame for frame in frames if frame.is_usable]
    if not usable_frames:
        return ViewInference("unknown", 0.0, {})

    frame_signals = [_frame_view_signal(frame) for frame in usable_frames]
    width_score = median(signal["width_score"] for signal in frame_signals)
    depth_score = median(signal["depth_score"] for signal in frame_signals)
    depth_to_width_ratio = median(signal["depth_to_width_ratio"] for signal in frame_signals)
    width_to_torso_ratio = median(signal["width_to_torso_ratio"] for signal in frame_signals)
    foot_profile_ratio = median(signal["foot_profile_ratio"] for signal in frame_signals)

    labels = [signal["label"] for signal in frame_signals]
    classified_labels = [label for label in labels if label != "unknown"]
    sagittal_votes = sum(1 for label in classified_labels if label == "sagittal")
    frontal_votes = sum(1 for label in classified_labels if label == "frontal")
    classified_count = len(classified_labels)
    total_count = len(frame_signals)
    top_label = "sagittal" if sagittal_votes >= frontal_votes else "frontal"
    top_votes = max(sagittal_votes, frontal_votes)
    vote_share = top_votes / max(classified_count, 1)
    classified_ratio = classified_count / max(total_count, 1)
    label_stability = _label_stability(labels)
    score_margin = mean(abs(signal["score_margin"]) for signal in frame_signals)
    consensus_confidence = (
        (vote_share * 0.45)
        + (classified_ratio * 0.2)
        + (label_stability * 0.2)
        + (min(score_margin / 0.2, 1.0) * 0.15)
    )

    signals = {
        "widthScore": width_score,
        "depthScore": depth_score,
        "depthToWidthRatio": depth_to_width_ratio,
        "widthToTorsoRatio": width_to_torso_ratio,
        "footProfileRatio": foot_profile_ratio,
        "classifiedRatio": classified_ratio,
        "voteShare": vote_share,
        "labelStability": label_stability,
        "scoreMargin": score_margin,
        "sagittalVotes": float(sagittal_votes),
        "frontalVotes": float(frontal_votes),
    }

    if classified_count == 0:
        return ViewInference("unknown", 0.0, signals)

    if vote_share < 0.72 or label_stability < 0.6 or score_margin < 0.035:
        return ViewInference("unknown", min(0.69, consensus_confidence), signals)

    return ViewInference(top_label, min(0.95, consensus_confidence), signals)


def _frame_view_signal(frame: FrameData) -> dict[str, float | str]:
    shoulder_width = abs(frame.joints["left_shoulder"].x - frame.joints["right_shoulder"].x)
    hip_width = abs(frame.joints["left_hip"].x - frame.joints["right_hip"].x)
    shoulder_depth = abs(frame.joints["left_shoulder"].z - frame.joints["right_shoulder"].z)
    hip_depth = abs(frame.joints["left_hip"].z - frame.joints["right_hip"].z)

    shoulder_center_y = (frame.joints["left_shoulder"].y + frame.joints["right_shoulder"].y) / 2.0
    hip_center_y = (frame.joints["left_hip"].y + frame.joints["right_hip"].y) / 2.0
    torso_height = max(abs(hip_center_y - shoulder_center_y), 1e-6)

    left_foot_index = frame.joints.get("left_foot_index", frame.joints["left_ankle"])
    right_foot_index = frame.joints.get("right_foot_index", frame.joints["right_ankle"])
    left_heel = frame.joints.get("left_heel", frame.joints["left_ankle"])
    right_heel = frame.joints.get("right_heel", frame.joints["right_ankle"])

    foot_stance_width = abs(left_foot_index.x - right_foot_index.x)
    left_foot_profile = abs(left_foot_index.x - left_heel.x)
    right_foot_profile = abs(right_foot_index.x - right_heel.x)

    width_score = (shoulder_width + hip_width) / 2.0
    depth_score = (shoulder_depth + hip_depth) / 2.0
    depth_to_width_ratio = depth_score / max(width_score, 1e-6)
    width_to_torso_ratio = width_score / torso_height
    foot_profile_ratio = ((left_foot_profile + right_foot_profile) / 2.0) / max(foot_stance_width, 1e-6)

    sagittal_score = (
        _clamp01((depth_to_width_ratio - 0.42) / 0.33) * 0.55
        + _clamp01((0.72 - width_to_torso_ratio) / 0.36) * 0.25
        + _clamp01((foot_profile_ratio - 0.22) / 0.28) * 0.2
    )
    frontal_score = (
        _clamp01((0.3 - depth_to_width_ratio) / 0.22) * 0.55
        + _clamp01((width_to_torso_ratio - 0.78) / 0.42) * 0.3
        + _clamp01((0.16 - foot_profile_ratio) / 0.1) * 0.15
    )
    score_margin = sagittal_score - frontal_score

    if max(sagittal_score, frontal_score) < 0.45 or abs(score_margin) < 0.08:
        label = "unknown"
    else:
        label = "sagittal" if score_margin > 0 else "frontal"

    return {
        "width_score": width_score,
        "depth_score": depth_score,
        "depth_to_width_ratio": depth_to_width_ratio,
        "width_to_torso_ratio": width_to_torso_ratio,
        "foot_profile_ratio": foot_profile_ratio,
        "sagittal_score": sagittal_score,
        "frontal_score": frontal_score,
        "score_margin": score_margin,
        "label": label,
    }


def _label_stability(labels: list[str]) -> float:
    classified_labels = [label for label in labels if label != "unknown"]
    if len(classified_labels) <= 1:
        return 1.0 if classified_labels else 0.0
    transitions = sum(
        1
        for idx in range(1, len(classified_labels))
        if classified_labels[idx] != classified_labels[idx - 1]
    )
    return 1.0 - (transitions / max(len(classified_labels) - 1, 1))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def extract_cop(
    frames: list[FrameData],
    features: FeatureSet,
    view_inference: ViewInference,
    bodyweight_kg: float | None = None,
    external_load_kg: float | None = None,
) -> tuple[GroundRef, FeatureSet]:
    usable_frames = [frame for frame in frames if frame.is_usable]
    if not usable_frames:
        return GroundRef(0.0, 0.0, 0.0, None, (0.0, 0.0), (0.0, 0.0), 0, "unknown", 0.0, {}, features.bar_placement_input, features.bar_placement_resolved, bodyweight_kg, external_load_kg, _total_mass(bodyweight_kg, external_load_kg)), features

    standing_frames = _standing_reference_frames(usable_frames)
    ground_y = median([_frame_ground_y(frame) for frame in standing_frames])
    mid_foot_x = median([_frame_mid_foot_x(frame) for frame in standing_frames])
    foot_width = median([_frame_foot_width(frame) for frame in standing_frames])
    sagittal_foot_length = median([_frame_sagittal_foot_length(frame) for frame in standing_frames])

    ground_ref = GroundRef(
        ground_y=ground_y,
        mid_foot_x=mid_foot_x,
        foot_width=foot_width,
        sagittal_foot_length=sagittal_foot_length if sagittal_foot_length > 0 else None,
        left_foot_vec=_median_vec(standing_frames, "left_heel", "left_foot_index", "left_ankle"),
        right_foot_vec=_median_vec(standing_frames, "right_heel", "right_foot_index", "right_ankle"),
        sample_frame_count=len(standing_frames),
        view_type=view_inference.view_type,
        view_confidence=view_inference.confidence,
        view_signals=view_inference.signals,
        bar_placement_input=features.bar_placement_input,
        bar_placement_resolved=features.bar_placement_resolved,
        bodyweight_kg=bodyweight_kg,
        external_load_kg=external_load_kg,
        total_system_mass_kg=_total_mass(bodyweight_kg, external_load_kg),
    )

    ap_scale = max(ground_ref.sagittal_foot_length or 0.0, 1e-6)
    ml_scale = max(ground_ref.foot_width, 1e-6)
    features.cop_ap_normalized = []
    features.cop_ml_normalized = []
    features.bar_over_midfoot = []

    for idx, frame in enumerate(usable_frames):
        bar_available = features.bar_confidence[idx] >= 0.5
        bar_x = features.bar_path_x[idx] if bar_available else None
        bar_y = features.bar_y[idx] if bar_available else None
        com_x, com_y = _resolve_system_com(
            body_com_x=features.body_com_x[idx],
            body_com_y=features.body_com_y[idx],
            bar_x=bar_x,
            bar_y=bar_y,
            bodyweight_kg=bodyweight_kg,
            external_load_kg=external_load_kg,
        )
        features.com_x[idx] = com_x
        features.com_y[idx] = com_y
        features.bar_com_offset[idx] = None if bar_x is None else bar_x - com_x
        if view_inference.view_type == "sagittal" and view_inference.confidence >= 0.7:
            features.cop_ap_normalized.append((com_x - ground_ref.mid_foot_x) / ap_scale)
            features.cop_ml_normalized.append(None)
        elif view_inference.view_type == "frontal" and view_inference.confidence >= 0.7:
            features.cop_ap_normalized.append(None)
            features.cop_ml_normalized.append((com_x - ground_ref.mid_foot_x) / ml_scale)
        else:
            features.cop_ap_normalized.append(None)
            features.cop_ml_normalized.append(None)

        features.moment_arms["left_ankle"][idx] = abs(com_x - frame.joints["left_ankle"].x)
        features.moment_arms["right_ankle"][idx] = abs(com_x - frame.joints["right_ankle"].x)
        features.moment_arms["left_knee"][idx] = abs(com_x - frame.joints["left_knee"].x)
        features.moment_arms["right_knee"][idx] = abs(com_x - frame.joints["right_knee"].x)
        features.moment_arms["left_hip"][idx] = abs(com_x - frame.joints["left_hip"].x)
        features.moment_arms["right_hip"][idx] = abs(com_x - frame.joints["right_hip"].x)
        features.bar_over_midfoot.append(None if bar_x is None else bar_x - ground_ref.mid_foot_x)

    return ground_ref, features


def _median_vec(
    frames: list[FrameData],
    start: str,
    end: str,
    fallback: str,
) -> tuple[float, float]:
    x_values = [_joint(frame, end, fallback).x - _joint(frame, start, fallback).x for frame in frames]
    y_values = [_joint(frame, end, fallback).y - _joint(frame, start, fallback).y for frame in frames]
    return (median(x_values), median(y_values))


def _resolve_system_com(
    body_com_x: float,
    body_com_y: float,
    bar_x: float | None,
    bar_y: float | None,
    bodyweight_kg: float | None,
    external_load_kg: float | None,
) -> tuple[float, float]:
    body_mass = bodyweight_kg or 0.0
    external_mass = external_load_kg or 0.0
    total_mass = body_mass + external_mass
    if total_mass <= 0:
        return body_com_x, body_com_y
    if external_mass <= 0:
        return body_com_x, body_com_y
    if bar_x is None or bar_y is None:
        return body_com_x, body_com_y
    if body_mass <= 0:
        return bar_x, bar_y
    return (
        ((body_com_x * body_mass) + (bar_x * external_mass)) / total_mass,
        ((body_com_y * body_mass) + (bar_y * external_mass)) / total_mass,
    )


def _total_mass(bodyweight_kg: float | None, external_load_kg: float | None) -> float | None:
    masses = [mass for mass in [bodyweight_kg, external_load_kg] if mass is not None]
    return round(sum(masses), 6) if masses else None


def _standing_reference_frames(frames: list[FrameData]) -> list[FrameData]:
    ranked = sorted(frames, key=_hip_center_y)
    count = max(5, len(ranked) // 5)
    return ranked[:count]


def _hip_center_y(frame: FrameData) -> float:
    return (frame.joints["left_hip"].y + frame.joints["right_hip"].y) / 2.0


def _joint(frame: FrameData, name: str, fallback: str) -> object:
    return frame.joints.get(name) or frame.joints[fallback]


def _frame_ground_y(frame: FrameData) -> float:
    left_heel = _joint(frame, "left_heel", "left_ankle")
    right_heel = _joint(frame, "right_heel", "right_ankle")
    left_foot_index = _joint(frame, "left_foot_index", "left_ankle")
    right_foot_index = _joint(frame, "right_foot_index", "right_ankle")
    return max(left_heel.y, right_heel.y, left_foot_index.y, right_foot_index.y)


def _frame_mid_foot_x(frame: FrameData) -> float:
    left_foot_index = _joint(frame, "left_foot_index", "left_ankle")
    right_foot_index = _joint(frame, "right_foot_index", "right_ankle")
    return (
        frame.joints["left_ankle"].x
        + frame.joints["right_ankle"].x
        + left_foot_index.x
        + right_foot_index.x
    ) / 4.0


def _frame_foot_width(frame: FrameData) -> float:
    left_foot_index = _joint(frame, "left_foot_index", "left_ankle")
    right_foot_index = _joint(frame, "right_foot_index", "right_ankle")
    return abs(left_foot_index.x - right_foot_index.x)


def _frame_sagittal_foot_length(frame: FrameData) -> float:
    left_foot_index = _joint(frame, "left_foot_index", "left_ankle")
    right_foot_index = _joint(frame, "right_foot_index", "right_ankle")
    left_heel = _joint(frame, "left_heel", "left_ankle")
    right_heel = _joint(frame, "right_heel", "right_ankle")
    return (abs(left_foot_index.x - left_heel.x) + abs(right_foot_index.x - right_heel.x)) / 2.0
