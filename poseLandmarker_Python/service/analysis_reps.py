from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from service.analysis_features import FeatureSet

MIN_REP_DURATION_MS = 500.0
MIN_PHASE_DURATION_MS = 180.0
MIN_PEAK_DISTANCE_MS = 450.0


@dataclass(slots=True)
class RepSegment:
    rep_index: int
    start_ms: float
    end_ms: float
    bottom_ms: float
    phase_eccentric_ms: float
    phase_concentric_ms: float
    depth_angle_deg: float

    def to_dict(self) -> dict:
        return {
            "repIndex": round(self.rep_index, 6),
            "startMs": round(self.start_ms, 6),
            "endMs": round(self.end_ms, 6),
            "bottomMs": round(self.bottom_ms, 6),
            "phaseEccentricMs": round(self.phase_eccentric_ms, 6),
            "phaseConcentricMs": round(self.phase_concentric_ms, 6),
            "depthAngleDeg": round(self.depth_angle_deg, 6),
        }


def detect_reps(features: FeatureSet, exercise_type: str | None = None) -> list[RepSegment]:
    if not features.timestamps_ms or len(features.timestamps_ms) < 7:
        return []

    timestamps = features.timestamps_ms
    hip_heights = features.hip_heights
    knee_left = features.joint_angles.get("left_knee_angle", [])
    knee_right = features.joint_angles.get("right_knee_angle", [])
    if len(hip_heights) != len(timestamps) or len(knee_left) != len(timestamps) or len(knee_right) != len(timestamps):
        return []

    smoothed = _triangular_smooth(hip_heights, window=7)
    velocity = _central_velocity(timestamps, smoothed)
    valleys = _find_valleys(smoothed)
    raw_peaks = _find_candidate_peaks(smoothed, velocity, valleys, timestamps)
    peaks = _dedupe_peaks(raw_peaks, timestamps, knee_left, knee_right)
    if not peaks:
        return []

    segments: list[RepSegment] = []
    last_end_idx = -1
    for peak_idx in peaks:
        start_idx, end_idx = _resolve_rep_bounds(peak_idx, valleys, smoothed, velocity, timestamps)
        if start_idx is None or end_idx is None:
            continue
        if start_idx <= last_end_idx:
            continue
        duration_ms = timestamps[end_idx] - timestamps[start_idx]
        eccentric_ms = timestamps[peak_idx] - timestamps[start_idx]
        concentric_ms = timestamps[end_idx] - timestamps[peak_idx]
        if duration_ms < MIN_REP_DURATION_MS:
            continue
        if eccentric_ms < MIN_PHASE_DURATION_MS or concentric_ms < MIN_PHASE_DURATION_MS:
            continue
        if not _passes_depth_gate(peak_idx, start_idx, end_idx, knee_left, knee_right):
            continue

        segments.append(
            RepSegment(
                rep_index=len(segments) + 1,
                start_ms=timestamps[start_idx],
                end_ms=timestamps[end_idx],
                bottom_ms=timestamps[peak_idx],
                phase_eccentric_ms=timestamps[start_idx],
                phase_concentric_ms=timestamps[peak_idx],
                depth_angle_deg=min(knee_left[peak_idx], knee_right[peak_idx]),
            )
        )
        last_end_idx = end_idx

    return segments


def _triangular_smooth(values: list[float], window: int) -> list[float]:
    if not values:
        return []
    radius = max(1, window // 2)
    smoothed: list[float] = []
    for idx in range(len(values)):
        weighted_sum = 0.0
        weight_total = 0.0
        for offset in range(-radius, radius + 1):
            source_idx = min(max(idx + offset, 0), len(values) - 1)
            weight = float(radius + 1 - abs(offset))
            weighted_sum += values[source_idx] * weight
            weight_total += weight
        smoothed.append(weighted_sum / max(weight_total, 1e-6))
    return smoothed


def _central_velocity(timestamps_ms: list[float], values: list[float]) -> list[float]:
    if len(values) <= 1:
        return [0.0] * len(values)
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


def _find_valleys(values: list[float]) -> list[int]:
    valleys = [0]
    valleys.extend(
        idx
        for idx in range(1, len(values) - 1)
        if values[idx] <= values[idx - 1] and values[idx] < values[idx + 1]
    )
    valleys.append(len(values) - 1)
    return sorted(set(valleys))


def _find_candidate_peaks(
    values: list[float],
    velocity: list[float],
    valleys: list[int],
    timestamps_ms: list[float],
) -> list[int]:
    if len(values) < 3:
        return []
    amplitude = max(values) - min(values)
    if amplitude <= 1e-6:
        return []
    min_prominence = max(amplitude * 0.18, 0.012)
    min_peak_height = min(values) + amplitude * 0.35
    candidates: list[int] = []
    for idx in range(1, len(values) - 1):
        if values[idx] < min_peak_height:
            continue
        if not (values[idx] >= values[idx - 1] and values[idx] > values[idx + 1]):
            continue
        left_valley = _nearest_left_boundary(valleys, idx, 0)
        right_valley = _nearest_right_boundary(valleys, idx, len(values) - 1)
        if left_valley >= idx or right_valley <= idx:
            continue
        prominence = values[idx] - max(values[left_valley], values[right_valley])
        if prominence < min_prominence:
            continue
        if not _has_phase_transition(idx, velocity):
            continue
        if (timestamps_ms[right_valley] - timestamps_ms[left_valley]) < MIN_REP_DURATION_MS:
            continue
        candidates.append(idx)
    return candidates


def _dedupe_peaks(
    peaks: list[int],
    timestamps_ms: list[float],
    knee_left: list[float],
    knee_right: list[float],
) -> list[int]:
    if not peaks:
        return []
    deduped = [peaks[0]]
    for idx in peaks[1:]:
        prev = deduped[-1]
        if (timestamps_ms[idx] - timestamps_ms[prev]) < MIN_PEAK_DISTANCE_MS:
            prev_depth = min(knee_left[prev], knee_right[prev])
            curr_depth = min(knee_left[idx], knee_right[idx])
            if curr_depth < prev_depth:
                deduped[-1] = idx
            continue
        deduped.append(idx)
    return deduped


def _resolve_rep_bounds(
    peak_idx: int,
    valleys: list[int],
    values: list[float],
    velocity: list[float],
    timestamps_ms: list[float],
) -> tuple[int | None, int | None]:
    start_idx = _nearest_left_boundary(valleys, peak_idx, default=0)
    end_idx = _nearest_right_boundary(valleys, peak_idx, default=len(values) - 1)
    start_idx = _refine_boundary(start_idx, peak_idx, values, velocity, direction="left")
    end_idx = _refine_boundary(end_idx, peak_idx, values, velocity, direction="right")
    if start_idx is None or end_idx is None:
        return None, None
    if start_idx >= peak_idx or end_idx <= peak_idx:
        return None, None
    if timestamps_ms[end_idx] - timestamps_ms[start_idx] < MIN_REP_DURATION_MS:
        return None, None
    return start_idx, end_idx


def _refine_boundary(
    boundary_idx: int,
    peak_idx: int,
    values: list[float],
    velocity: list[float],
    direction: str,
) -> int | None:
    if direction == "left":
        search_range = range(boundary_idx, peak_idx)
        best_idx = boundary_idx
        best_value = values[boundary_idx]
        for idx in search_range:
            if values[idx] <= best_value:
                best_value = values[idx]
                best_idx = idx
            if idx < peak_idx - 1 and velocity[idx] <= 0 < velocity[idx + 1]:
                best_idx = idx
        return best_idx

    search_range = range(peak_idx + 1, boundary_idx + 1)
    best_idx = boundary_idx
    best_value = values[boundary_idx]
    for idx in search_range:
        if values[idx] <= best_value:
            best_value = values[idx]
            best_idx = idx
        if idx > peak_idx + 1 and velocity[idx - 1] < 0 <= velocity[idx]:
            best_idx = idx
            break
    return best_idx


def _has_phase_transition(peak_idx: int, velocity: list[float]) -> bool:
    left_window = velocity[max(0, peak_idx - 3):peak_idx]
    right_window = velocity[peak_idx + 1:min(len(velocity), peak_idx + 4)]
    if not left_window or not right_window:
        return False
    return mean(left_window) > 0 and mean(right_window) < 0


def _passes_depth_gate(
    peak_idx: int,
    start_idx: int,
    end_idx: int,
    knee_left: list[float],
    knee_right: list[float],
) -> bool:
    peak_depth = min(knee_left[peak_idx], knee_right[peak_idx])
    boundary_depth = mean(
        [
            min(knee_left[start_idx], knee_right[start_idx]),
            min(knee_left[end_idx], knee_right[end_idx]),
        ]
    )
    return peak_depth + 8.0 < boundary_depth


def _nearest_left_boundary(indices: list[int], center: int, default: int) -> int:
    candidates = [idx for idx in indices if idx < center]
    return candidates[-1] if candidates else default


def _nearest_right_boundary(indices: list[int], center: int, default: int) -> int:
    candidates = [idx for idx in indices if idx > center]
    return candidates[0] if candidates else default
