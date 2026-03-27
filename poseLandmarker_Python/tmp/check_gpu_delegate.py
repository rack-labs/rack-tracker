from pathlib import Path
import traceback

import mediapipe as mp
from mediapipe.tasks.python import vision


def main() -> None:
    model_path = Path("models/mediapipe/pose_landmarker_full.task").resolve()
    print(f"mediapipe={mp.__version__}")
    print(f"model_path={model_path}")
    print(f"delegate_enum={getattr(mp.tasks.BaseOptions, 'Delegate', None)}")

    try:
        base_options = mp.tasks.BaseOptions(
            model_asset_path=str(model_path),
            delegate=mp.tasks.BaseOptions.Delegate.GPU,
        )
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        landmarker = vision.PoseLandmarker.create_from_options(options)
        print("gpu_init=success")
        landmarker.close()
    except Exception as exc:
        print(f"gpu_init=failed: {exc.__class__.__name__}: {exc}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
