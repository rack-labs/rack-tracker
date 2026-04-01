import os
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "tmp"
UPLOAD_DIR = TEMP_DIR / "uploads"
EXTRACTED_FRAME_DIR = TEMP_DIR / "frames"
BENCHMARK_DIR = TEMP_DIR / "benchmarks"
SKELETON_DIR = TEMP_DIR / "skeletons"
DEFAULT_MODEL_DIR = BASE_DIR / "models" / "mediapipe"
MODEL_DIR = Path(os.getenv("POSE_MODEL_DIR", "").strip() or DEFAULT_MODEL_DIR)
MODEL_ASSET_PATHS = {
    "lite": MODEL_DIR / "pose_landmarker_lite.task",
    "full": MODEL_DIR / "pose_landmarker_full.task",
    "heavy": MODEL_DIR / "pose_landmarker_heavy.task",
}
DEFAULT_MODEL_VARIANT = "full"
DEFAULT_MODEL_ASSET_PATH = MODEL_ASSET_PATHS[DEFAULT_MODEL_VARIANT]
MOCK_VIDEO_PATH = BASE_DIR / "src" / "video" / "backSquat.mp4"
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
TEMP_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_FRAME_DIR.mkdir(parents=True, exist_ok=True)
BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
SKELETON_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
