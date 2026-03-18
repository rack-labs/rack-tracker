from pathlib import Path

paths = [
    Path(r"C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\docs\features\mediapipe\decision-checklist-phase-1-index-01.md"),
    Path(r"C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\docs\features\mediapipe\architecture.md"),
    Path(r"C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\docs\features\mediapipe\spec.md"),
]

for path in paths:
    print(f"===== {path} =====")
    print(path.read_text(encoding="utf-8"))
