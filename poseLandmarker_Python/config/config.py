from pathlib import Path

HOST = "127.0.0.1"
PORT = 8000
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "tmp"
UPLOAD_DIR = TEMP_DIR / "uploads"
EXTRACTED_FRAME_DIR = TEMP_DIR / "frames"
MOCK_VIDEO_PATH = BASE_DIR / "src" / "video" / "backSquat.mp4"
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

TEMP_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_FRAME_DIR.mkdir(parents=True, exist_ok=True)
