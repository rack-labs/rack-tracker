from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, hypot
from statistics import median

from service.analysis_preprocess import FrameData, JointData


@dataclass(slots=True)
class BodyProfile:
    left_femur_len: float
    right_femur_len: float
    left_tibia_len: float
    right_tibia_len: float
    torso_len: float
    left_upper_arm_len: float
    right_upper_arm_len: float
    femur_to_torso_ratio: float
    tibia_to_femur_ratio: float
    limb_asymmetry: dict[str, float]
    joint_angle_baseline_deg: dict[str, float]
    sample_frame_count: int

    def to_dict(self) -> dict:
        return {
            "leftFemurLen": round(self.left_femur_len, 6),
            "rightFemurLen": round(self.right_femur_len, 6),
            "leftTibiaLen": round(self.left_tibia_len, 6),
            "rightTibiaLen": round(self.right_tibia_len, 6),
            "torsoLen": round(self.torso_len, 6),
            "leftUpperArmLen": round(self.left_upper_arm_len, 6),
            "rightUpperArmLen": round(self.right_upper_arm_len, 6),
            "femurToTorsoRatio": round(self.femur_to_torso_ratio, 6),
            "tibiaToFemurRatio": round(self.tibia_to_femur_ratio, 6),
            "limbAsymmetry": {key: round(value, 6) for key, value in self.limb_asymmetry.items()},
            "jointAngleBaselineDeg": {
                key: round(value, 6) for key, value in self.joint_angle_baseline_deg.items()
            },
            "sampleFrameCount": self.sample_frame_count,
        }


def extract_body_profile(frames: list[FrameData]) -> BodyProfile:
    usable_frames = [frame for frame in frames if frame.is_usable]
    if not usable_frames:
        return BodyProfile(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, {"femur": 0.0, "tibia": 0.0, "upperArm": 0.0}, {"knee": 0.0, "hip": 0.0}, 0)

    standing_frames = _standing_frames(usable_frames)
    left_femur = _median_distance(usable_frames, "left_hip", "left_knee")
    right_femur = _median_distance(usable_frames, "right_hip", "right_knee")
    left_tibia = _median_distance(usable_frames, "left_knee", "left_ankle")
    right_tibia = _median_distance(usable_frames, "right_knee", "right_ankle")
    torso = _median_torso_len(usable_frames)
    left_upper_arm = _median_distance(usable_frames, "left_shoulder", "left_elbow")
    right_upper_arm = _median_distance(usable_frames, "right_shoulder", "right_elbow")

    mean_femur = _mean(left_femur, right_femur)
    mean_tibia = _mean(left_tibia, right_tibia)
    joint_baselines = {
        "knee": _median_joint_diff(
            standing_frames,
            ("left_hip", "left_knee", "left_ankle"),
            ("right_hip", "right_knee", "right_ankle"),
        ),
        "hip": _median_joint_diff(
            standing_frames,
            ("left_shoulder", "left_hip", "left_knee"),
            ("right_shoulder", "right_hip", "right_knee"),
        ),
    }

    return BodyProfile(
        left_femur_len=left_femur,
        right_femur_len=right_femur,
        left_tibia_len=left_tibia,
        right_tibia_len=right_tibia,
        torso_len=torso,
        left_upper_arm_len=left_upper_arm,
        right_upper_arm_len=right_upper_arm,
        femur_to_torso_ratio=mean_femur / max(torso, 1e-6),
        tibia_to_femur_ratio=mean_tibia / max(mean_femur, 1e-6),
        limb_asymmetry={
            "femur": _relative_diff(left_femur, right_femur),
            "tibia": _relative_diff(left_tibia, right_tibia),
            "upperArm": _relative_diff(left_upper_arm, right_upper_arm),
        },
        joint_angle_baseline_deg=joint_baselines,
        sample_frame_count=len(usable_frames),
    )


def point(joint: JointData) -> tuple[float, float]:
    return (joint.x, joint.y)


def midpoint(a: JointData, b: JointData) -> tuple[float, float]:
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)


def distance(a: JointData, b: JointData) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def calc_angle(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    denominator = (hypot(*ba) * hypot(*bc)) or 1e-9
    cosine = ((ba[0] * bc[0]) + (ba[1] * bc[1])) / denominator
    cosine = max(-1.0, min(1.0, cosine))
    return degrees(acos(cosine))


def _standing_frames(frames: list[FrameData]) -> list[FrameData]:
    ranked = sorted(frames, key=_hip_center_y)
    count = max(5, len(ranked) // 5)
    return ranked[:count]


def _hip_center_y(frame: FrameData) -> float:
    left = frame.joints["left_hip"]
    right = frame.joints["right_hip"]
    return (left.y + right.y) / 2.0


def _median_distance(frames: list[FrameData], a: str, b: str) -> float:
    values = [distance(frame.joints[a], frame.joints[b]) for frame in frames if a in frame.joints and b in frame.joints]
    return median(values) if values else 0.0


def _median_torso_len(frames: list[FrameData]) -> float:
    values: list[float] = []
    for frame in frames:
        shoulder = midpoint(frame.joints["left_shoulder"], frame.joints["right_shoulder"])
        hip = midpoint(frame.joints["left_hip"], frame.joints["right_hip"])
        values.append(hypot(shoulder[0] - hip[0], shoulder[1] - hip[1]))
    return median(values) if values else 0.0


def _median_joint_diff(
    frames: list[FrameData],
    left_triplet: tuple[str, str, str],
    right_triplet: tuple[str, str, str],
) -> float:
    values: list[float] = []
    for frame in frames:
        left_angle = calc_angle(point(frame.joints[left_triplet[0]]), point(frame.joints[left_triplet[1]]), point(frame.joints[left_triplet[2]]))
        right_angle = calc_angle(point(frame.joints[right_triplet[0]]), point(frame.joints[right_triplet[1]]), point(frame.joints[right_triplet[2]]))
        values.append(abs(left_angle - right_angle))
    return median(values) if values else 0.0


def _relative_diff(left: float, right: float) -> float:
    return abs(left - right) / max((left + right) / 2.0, 1e-6)


def _mean(left: float, right: float) -> float:
    return (left + right) / 2.0
