import argparse
import json
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


LANDMARK_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract pose landmarks from a still image."
    )
    parser.add_argument(
        "--image",
        default="../images/training-quad-focused-squat-variations-main-1024x683.jpg",
        help="Path to the input image.",
    )
    parser.add_argument(
        "--model",
        default="pose_landmarker_lite.task",
        help="Path to the MediaPipe pose landmarker task file.",
    )
    parser.add_argument(
        "--output-image",
        default="pose_output.png",
        help="Path to save the annotated image.",
    )
    parser.add_argument(
        "--output-json",
        default="pose_output.json",
        help="Path to save labeled skeleton data.",
    )
    return parser.parse_args()


def ensure_model_exists(model_path: Path) -> None:
    if model_path.exists():
        return

    raise FileNotFoundError(
        f"Model file not found: {model_path}\n"
        f"Download it from:\n{MODEL_URL}"
    )


def ensure_image_exists(image_path: Path) -> None:
    if image_path.exists():
        return

    raise FileNotFoundError(f"Image file not found: {image_path}")


def create_landmarker(model_path: Path) -> vision.PoseLandmarker:
    common_kwargs = {
        "running_mode": vision.RunningMode.IMAGE,
        "num_poses": 1,
        "min_pose_detection_confidence": 0.5,
        "min_pose_presence_confidence": 0.5,
        "min_tracking_confidence": 0.5,
        "output_segmentation_masks": False,
    }

    try:
        gpu_options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(
                model_asset_path=str(model_path),
                delegate=python.BaseOptions.Delegate.GPU,
            ),
            **common_kwargs,
        )
        return vision.PoseLandmarker.create_from_options(gpu_options)
    except RuntimeError:
        cpu_options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(
                model_asset_path=str(model_path),
                delegate=python.BaseOptions.Delegate.CPU,
            ),
            **common_kwargs,
        )
        return vision.PoseLandmarker.create_from_options(cpu_options)


def label_skeleton(result: vision.PoseLandmarkerResult) -> list[dict]:
    if not result.pose_landmarks:
        return []

    skeleton = []
    for index, joint in enumerate(result.pose_landmarks[0]):
        skeleton.append(
            {
                "id": index,
                "jointName": LANDMARK_NAMES[index],
                "x": joint.x,
                "y": joint.y,
                "z": joint.z,
                "visibility": joint.visibility,
            }
        )
    return skeleton


def draw_pose(image_path: Path, result: vision.PoseLandmarkerResult) -> cv2.typing.MatLike:
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {image_path}")

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    drawing_utils = mp.solutions.drawing_utils
    drawing_styles = mp.solutions.drawing_styles
    pose_connections = mp.solutions.pose.POSE_CONNECTIONS

    for landmarks in result.pose_landmarks:
        landmark_proto = landmark_pb2.NormalizedLandmarkList()
        landmark_proto.landmark.extend(
            landmark_pb2.NormalizedLandmark(
                x=landmark.x,
                y=landmark.y,
                z=landmark.z,
                visibility=landmark.visibility,
            )
            for landmark in landmarks
        )

        drawing_utils.draw_landmarks(
            rgb_image,
            landmark_proto,
            pose_connections,
            landmark_drawing_spec=drawing_styles.get_default_pose_landmarks_style(),
        )

    return cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    image_path = (script_dir / args.image).resolve()
    model_path = (script_dir / args.model).resolve()
    output_image_path = (script_dir / args.output_image).resolve()
    output_json_path = (script_dir / args.output_json).resolve()

    ensure_image_exists(image_path)
    ensure_model_exists(model_path)

    mp_image = mp.Image.create_from_file(str(image_path))

    with create_landmarker(model_path) as landmarker:
        result = landmarker.detect(mp_image)

    labeled_skeleton = label_skeleton(result)
    print(json.dumps(labeled_skeleton, indent=4))

    output_json_path.write_text(
        json.dumps(labeled_skeleton, indent=4),
        encoding="utf-8",
    )

    annotated_image = draw_pose(image_path, result)
    cv2.imwrite(str(output_image_path), annotated_image)


if __name__ == "__main__":
    main()
