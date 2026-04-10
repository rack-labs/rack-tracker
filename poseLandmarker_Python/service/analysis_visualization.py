from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any

from service.analysis_cop import GroundRef
from service.analysis_features import FeatureSet
from service.analysis_preprocess import FrameData
from service.analysis_reps import RepSegment
from service.analysis_thresholds import PersonalThresholds

MAX_FRAME_OVERLAYS = 12


@dataclass(slots=True)
class VisualizationOverlay:
    frame_index: int
    timestamp_ms: float
    points: dict[str, list[float] | None]
    lines: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frameIndex": self.frame_index,
            "timestampMs": round(self.timestamp_ms, 6),
            "points": self.points,
            "lines": self.lines,
        }


def build_visualization(
    clean_frames: list[FrameData],
    features: FeatureSet,
    ground_ref: GroundRef,
    rep_segments: list[RepSegment],
    thresholds: PersonalThresholds,
) -> dict[str, Any]:
    usable_frames = [frame for frame in clean_frames if frame.is_usable]
    overlays: list[VisualizationOverlay] = []
    overlay_indices = _select_overlay_indices(features, rep_segments)

    for feature_idx in overlay_indices:
        if feature_idx >= len(usable_frames):
            continue
        frame = usable_frames[feature_idx]
        points = _build_points(feature_idx, ground_ref, features)
        lines = _build_lines(feature_idx, ground_ref, features, points)
        overlays.append(
            VisualizationOverlay(
                frame_index=frame.frame_index,
                timestamp_ms=frame.timestamp_ms,
                points=points,
                lines=lines,
            )
        )

    return {
        "viewType": ground_ref.view_type,
        "viewConfidence": round(ground_ref.view_confidence, 6),
        "frameOverlays": [overlay.to_dict() for overlay in overlays],
        "chartHints": {
            "copBands": _cop_bands(ground_ref, thresholds),
            "barMidfootTolerance": round(thresholds.bar_midfoot_offset_warn, 6),
            "repBottomsMs": [round(rep.bottom_ms, 6) for rep in rep_segments],
            "repRangesMs": [
                [round(rep.start_ms, 6), round(rep.end_ms, 6)]
                for rep in rep_segments
            ],
            "recommendedCharts": _recommended_charts(ground_ref),
        },
    }


def _select_overlay_indices(features: FeatureSet, rep_segments: list[RepSegment]) -> list[int]:
    if not features.timestamps_ms:
        return []

    indices: set[int] = set()
    for rep in rep_segments:
        indices.add(_closest_index(features.timestamps_ms, rep.start_ms))
        indices.add(_closest_index(features.timestamps_ms, rep.bottom_ms))
        indices.add(_closest_index(features.timestamps_ms, rep.end_ms))

    if not indices:
        sample_count = min(len(features.timestamps_ms), max(3, min(MAX_FRAME_OVERLAYS, len(features.timestamps_ms))))
        if sample_count == len(features.timestamps_ms):
            return list(range(len(features.timestamps_ms)))
        step = max((len(features.timestamps_ms) - 1) / max(sample_count - 1, 1), 1.0)
        return sorted({round(step * idx) for idx in range(sample_count)})

    if len(indices) > MAX_FRAME_OVERLAYS:
        bottom_indices = sorted(_closest_index(features.timestamps_ms, rep.bottom_ms) for rep in rep_segments)
        prioritized = bottom_indices[:MAX_FRAME_OVERLAYS]
        return sorted(set(prioritized))
    return sorted(indices)


def _build_points(
    feature_idx: int,
    ground_ref: GroundRef,
    features: FeatureSet,
) -> dict[str, list[float] | None]:
    cop_x = None
    if feature_idx < len(features.com_x):
        if features.cop_ap_normalized[feature_idx] is not None or features.cop_ml_normalized[feature_idx] is not None:
            cop_x = features.com_x[feature_idx]

    bar_point = None
    if feature_idx < len(features.bar_confidence) and features.bar_confidence[feature_idx] >= 0.5:
        bar_point = [
            round(features.bar_path_x[feature_idx], 6),
            round(features.bar_y[feature_idx], 6),
        ]

    return {
        "midFoot": [round(ground_ref.mid_foot_x, 6), round(ground_ref.ground_y, 6)],
        "com": [round(features.com_x[feature_idx], 6), round(features.com_y[feature_idx], 6)],
        "cop": None if cop_x is None else [round(cop_x, 6), round(ground_ref.ground_y, 6)],
        "bar": bar_point,
    }


def _build_lines(
    feature_idx: int,
    ground_ref: GroundRef,
    features: FeatureSet,
    points: dict[str, list[float] | None],
) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = [
        {"type": "vertical", "x": round(ground_ref.mid_foot_x, 6), "label": "midfoot"},
    ]
    cop_point = points.get("cop")
    if cop_point is not None:
        lines.append({"type": "vertical", "x": cop_point[0], "label": "cop"})
    bar_point = points.get("bar")
    if bar_point is not None:
        lines.append({"type": "vertical", "x": bar_point[0], "label": "bar"})

    if feature_idx < len(features.bar_confidence) and features.bar_confidence[feature_idx] < 0.5:
        lines.append(
            {
                "type": "status",
                "label": "bar_estimate_low_confidence",
                "confidence": round(features.bar_confidence[feature_idx], 6),
            }
        )
    return lines


def _cop_bands(ground_ref: GroundRef, thresholds: PersonalThresholds) -> list[float]:
    if ground_ref.view_type == "frontal":
        band = thresholds.cop_ml_range
    else:
        band = thresholds.cop_ap_range
    return [round(-band, 6), round(band, 6)]


def _recommended_charts(ground_ref: GroundRef) -> list[str]:
    charts = ["bar_com_offset", "bar_over_midfoot", "knee_hip_moment_ratio"]
    if ground_ref.view_type == "frontal":
        return ["cop_ml_normalized", *charts]
    if ground_ref.view_type == "sagittal":
        return ["cop_ap_normalized", *charts]
    return charts


def _closest_index(values: list[float], target: float) -> int:
    return min(range(len(values)), key=lambda idx: abs(values[idx] - target))
