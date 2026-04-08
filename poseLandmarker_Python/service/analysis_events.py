from __future__ import annotations

from dataclasses import dataclass

from service.analysis_reps import RepSegment


@dataclass(slots=True)
class Event:
    type: str
    timestamp_ms: float
    rep_index: int | None
    metadata: dict

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "timestampMs": round(self.timestamp_ms, 6),
            "repIndex": self.rep_index,
            "metadata": self.metadata,
        }


def detect_events(frames_raw: list[dict], rep_segments: list[RepSegment]) -> list[Event]:
    events: list[Event] = []
    events.extend(_pose_detection_events(frames_raw, rep_segments))
    for rep in rep_segments:
        events.extend(
            [
                Event("rep_start", rep.start_ms, rep.rep_index, {}),
                Event("rep_bottom", rep.bottom_ms, rep.rep_index, {"knee_angle": round(rep.depth_angle_deg, 6)}),
                Event("rep_end", rep.end_ms, rep.rep_index, {}),
            ]
        )
    return sorted(events, key=lambda event: (event.timestamp_ms, event.type))


def _pose_detection_events(frames_raw: list[dict], rep_segments: list[RepSegment]) -> list[Event]:
    if not frames_raw:
        return []

    sorted_frames = sorted(frames_raw, key=lambda frame: float(frame.get("timestampMs") or 0.0))
    events: list[Event] = []
    miss_start_idx: int | None = None

    for idx, frame in enumerate(sorted_frames):
        pose_detected = bool(frame.get("poseDetected"))
        if not pose_detected and miss_start_idx is None:
            miss_start_idx = idx
            timestamp_ms = float(frame.get("timestampMs") or 0.0)
            events.append(
                Event(
                    "pose_lost",
                    timestamp_ms,
                    _rep_index_for_timestamp(timestamp_ms, rep_segments),
                    {"frameIndex": int(frame.get("frameIndex") or 0)},
                )
            )
            continue

        if pose_detected and miss_start_idx is not None:
            miss_start_frame = sorted_frames[miss_start_idx]
            previous_frame = sorted_frames[idx - 1]
            recovered_timestamp_ms = float(frame.get("timestampMs") or 0.0)
            events.append(
                Event(
                    "pose_recovered",
                    recovered_timestamp_ms,
                    _rep_index_for_timestamp(recovered_timestamp_ms, rep_segments),
                    {
                        "frameIndex": int(frame.get("frameIndex") or 0),
                        "missedFrameCount": idx - miss_start_idx,
                        "lostTimestampMs": round(float(miss_start_frame.get("timestampMs") or 0.0), 6),
                        "lostDurationMs": round(
                            float(previous_frame.get("timestampMs") or 0.0)
                            - float(miss_start_frame.get("timestampMs") or 0.0),
                            6,
                        ),
                    },
                )
            )
            miss_start_idx = None

    return events


def _rep_index_for_timestamp(timestamp_ms: float, rep_segments: list[RepSegment]) -> int | None:
    for rep in rep_segments:
        if rep.start_ms <= timestamp_ms <= rep.end_ms:
            return rep.rep_index
    return None
