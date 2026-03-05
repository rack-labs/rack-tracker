// 초기 로딩 관리 추가 필요

import {
    PoseLandmarker,
    FilesetResolver,
    DrawingUtils
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest";

let poseLandmaker = undefined;

// Configurations options
let delegate = "GPU";
let runningMode = "IMAGE";
let numPoses = "1";
let minPoseDetectionConfidence = "0.5";
let minPosePresenceConfidence = "0.5";
let minTrackingConfidence = "0.5";
let outputSegmentationMasks = "False";
let resultCallback = "N/A";

const videoHeight = "360px";
const videoWidth = "480px";

const createPoseLandmarker = async () =>{
    const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );
    poseLandmaker = await PoseLandmarker.createFromOptions(vision, {
        modelAssetPath: //Lite model
                "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
            delegate: delegate,
        runningMode: runningMode,
        numPoses: numPoses,
        minPoseDetectionConfidence: minPoseDetectionConfidence,
        minPosePresenceConfidence: minPosePresenceConfidence,
        minTrackingConfidence: minTrackingConfidence,
        outputSegmentationMasks: outputSegmentationMasks,
        resultCallback: resultCallback,
    });
};
createPoseLandmarker();