from pathlib import Path

paths = [
    Path(r"C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\docs\mvp-v1\features\mediapipe\core\decision-checklist-phase-1-index-01.md"),
    Path(r"C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\docs\mvp-v1\features\mediapipe\core\architecture.md"),
    Path(r"C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\docs\mvp-v1\features\mediapipe\core\spec.md"),
]

for path in paths:
    print(f"===== {path} =====")
    print(path.read_text(encoding="utf-8"))
