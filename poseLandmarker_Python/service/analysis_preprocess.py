from __future__ import annotations

from dataclasses import dataclass

VISIBILITY_THRESHOLD = 0.5
MAX_GAP_FRAMES = 3
SQUAT_REQUIRED_JOINTS = {
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_shoulder",
    "right_shoulder",
}


@dataclass(slots=True)
class JointData:
    name: str
    x: float
    y: float
    z: float
    visibility: float
    presence: float | None
    is_reliable: bool


@dataclass(slots=True)
class FrameData:
    frame_index: int
    timestamp_ms: float
    pose_detected: bool
    joints: dict[str, JointData]
    is_usable: bool


def preprocess(
    frames_raw: list[dict],
    visibility_threshold: float = VISIBILITY_THRESHOLD,
    required_joints: set[str] | None = None,
) -> list[FrameData]:
    required = required_joints or SQUAT_REQUIRED_JOINTS
    clean_frames: list[FrameData] = []

    for frame in sorted(frames_raw, key=lambda item: float(item.get("timestampMs") or 0.0)):
        joints: dict[str, JointData] = {}
        for landmark in frame.get("landmarks", []):
            visibility = float(landmark.get("visibility") or 0.0)
            joint = JointData(
                name=str(landmark.get("name") or ""),
                x=float(landmark.get("x") or 0.0),
                y=float(landmark.get("y") or 0.0),
                z=float(landmark.get("z") or 0.0),
                visibility=visibility,
                presence=_maybe_float(landmark.get("presence")),
                is_reliable=visibility >= visibility_threshold,
            )
            if joint.name:
                joints[joint.name] = joint

        pose_detected = bool(frame.get("poseDetected"))
        is_usable = pose_detected and all(
            joint_name in joints and joints[joint_name].is_reliable for joint_name in required
        )
        clean_frames.append(
            FrameData(
                frame_index=int(frame.get("frameIndex") or 0),
                timestamp_ms=float(frame.get("timestampMs") or 0.0),
                pose_detected=pose_detected,
                joints=joints,
                is_usable=is_usable,
            )
        )

    return _fill_short_unusable_gaps(clean_frames, required)


def _fill_short_unusable_gaps(frames: list[FrameData], required_joints: set[str]) -> list[FrameData]:
    if not frames:
        return frames

    index = 0
    while index < len(frames):
        if frames[index].is_usable:
            index += 1
            continue

        start = index
        while index < len(frames) and not frames[index].is_usable:
            index += 1
        end = index - 1
        gap_size = end - start + 1

        if gap_size > MAX_GAP_FRAMES or start == 0 or index >= len(frames):
            continue

        left = frames[start - 1]
        right = frames[index]
        if not left.is_usable or not right.is_usable:
            continue
        if not all(name in left.joints and name in right.joints for name in required_joints):
            continue

        for gap_offset, frame_idx in enumerate(range(start, end + 1), start=1):
            alpha = gap_offset / (gap_size + 1)
            original = frames[frame_idx]
            interpolated_joints = dict(original.joints)
            for joint_name in required_joints:
                interpolated_joints[joint_name] = _interpolate_joint(
                    joint_name,
                    left.joints[joint_name],
                    right.joints[joint_name],
                    alpha,
                )
            frames[frame_idx] = FrameData(
                frame_index=original.frame_index,
                timestamp_ms=original.timestamp_ms,
                pose_detected=True,
                joints=interpolated_joints,
                is_usable=True,
            )

    return frames


def _interpolate_joint(name: str, left: JointData, right: JointData, alpha: float) -> JointData:
    return JointData(
        name=name,
        x=_lerp(left.x, right.x, alpha),
        y=_lerp(left.y, right.y, alpha),
        z=_lerp(left.z, right.z, alpha),
        visibility=min(left.visibility, right.visibility),
        presence=left.presence if left.presence is not None else right.presence,
        is_reliable=True,
    )


def _lerp(start: float, end: float, alpha: float) -> float:
    return start + (end - start) * alpha


def _maybe_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
