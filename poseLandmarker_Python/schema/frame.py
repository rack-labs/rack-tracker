from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SamplingMode = Literal["all", "every_n_frames", "target_fps", "time_range"]


@dataclass(slots=True)
class FrameExtractionOptions:
    video_path: Path
    sampling_mode: SamplingMode = "all"
    every_n_frames: int | None = None
    target_fps: float | None = None
    start_ms: float | None = None
    end_ms: float | None = None
    output_dir: Path | None = None
    save_images: bool = False
    image_extension: str = "jpg"
    jpeg_quality: int = 95
    convert_bgr_to_rgb: bool = False


@dataclass(slots=True)
class ExtractedFrame:
    index: int
    timestamp_ms: float
    timestamp_sec: float
    backend: str
    width: int
    height: int
    image: object | None
    saved_path: Path | None


@dataclass(slots=True)
class FrameExtractionResult:
    source_path: Path
    backend: str
    source_fps: float
    frame_count: int | None
    width: int | None
    height: int | None
    extracted_count: int
    frames: list[ExtractedFrame]
