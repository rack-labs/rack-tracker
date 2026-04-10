from __future__ import annotations

from pathlib import Path
from typing import Any


class OpenCvAdapterError(Exception):
    pass


class VideoSourceNotFoundError(OpenCvAdapterError):
    pass


class VideoOpenError(OpenCvAdapterError):
    pass


class VideoMetadataError(OpenCvAdapterError):
    pass


class FrameReadError(OpenCvAdapterError):
    pass


class FrameWriteError(OpenCvAdapterError):
    pass


class OpenCvAdapter:
    def __init__(self) -> None:
        self._cv2 = self._import_cv2()
        self._capture: Any | None = None

    def _import_cv2(self) -> Any:
        try:
            import cv2
        except ModuleNotFoundError as exc:
            raise OpenCvAdapterError(
                "OpenCV is not installed. Run `uv sync` to install project dependencies."
            ) from exc
        return cv2

    def open_video(self, video_path: str) -> None:
        path = Path(video_path)
        if not path.exists():
            raise VideoSourceNotFoundError(f"Video source not found: {path}")

        self.close()
        self._capture = self._cv2.VideoCapture(str(path))
        if not self.is_opened():
            self.close()
            raise VideoOpenError(f"Failed to open video source: {path}")

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def is_opened(self) -> bool:
        return self._capture is not None and bool(self._capture.isOpened())

    def get_metadata(self) -> dict[str, Any]:
        if not self.is_opened():
            raise VideoMetadataError("Video is not opened.")

        metadata = {
            "fps": float(self._capture.get(self._cv2.CAP_PROP_FPS) or 0.0),
            "frame_count": int(self._capture.get(self._cv2.CAP_PROP_FRAME_COUNT) or 0),
            "width": int(self._capture.get(self._cv2.CAP_PROP_FRAME_WIDTH) or 0),
            "height": int(self._capture.get(self._cv2.CAP_PROP_FRAME_HEIGHT) or 0),
            "backend_id": int(self._capture.get(self._cv2.CAP_PROP_BACKEND) or -1),
            "backend": self.backend_name(),
        }
        return metadata

    def seek_frame(self, frame_index: int) -> bool:
        if not self.is_opened():
            raise FrameReadError("Video is not opened.")
        return bool(self._capture.set(self._cv2.CAP_PROP_POS_FRAMES, frame_index))

    def read_frame(self) -> tuple[bool, Any | None]:
        if not self.is_opened():
            raise FrameReadError("Video is not opened.")
        ok, frame = self._capture.read()
        return bool(ok), frame

    def current_timestamp_ms(self) -> float:
        if not self.is_opened():
            raise FrameReadError("Video is not opened.")
        return float(self._capture.get(self._cv2.CAP_PROP_POS_MSEC) or 0.0)

    def backend_name(self) -> str:
        if not self.is_opened():
            return "unknown"
        if hasattr(self._capture, "getBackendName"):
            try:
                return str(self._capture.getBackendName())
            except Exception:
                return "unknown"
        return "unknown"

    def convert_bgr_to_rgb(self, frame: Any) -> Any:
        return self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)

    def resize_by_width(self, frame: Any, width: int) -> Any:
        height = int(frame.shape[0] * (width / frame.shape[1]))
        return self._cv2.resize(frame, (width, height))

    def write_frame(
        self,
        frame: Any,
        output_path: Path,
        image_extension: str,
        jpeg_quality: int,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        params: list[int] = []
        if image_extension.lower() in {"jpg", "jpeg"}:
            params = [self._cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
        if not self._cv2.imwrite(str(output_path), frame, params):
            raise FrameWriteError(f"Failed to write frame to {output_path}")
        return output_path
