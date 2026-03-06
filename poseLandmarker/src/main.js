// 초기 로딩 관리 추가 필요

import {
    PoseLandmarker,
    FilesetResolver,
    DrawingUtils, 
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest";

let poseLandmarker = undefined;

// Configurations options
let delegate = "GPU";
let runningMode = "IMAGE";
let numPoses = 1;
let minPoseDetectionConfidence = 0.5;
let minPosePresenceConfidence = 0.5;
let minTrackingConfidence = 0.5;
let outputSegmentationMasks = false;
let resultCallback = "N/A";

// landmarkNames 
const landmarkNames = [
    "nose",
    "left_eye_inner","left_eye","left_eye_outer",
    "right_eye_inner","right_eye","right_eye_outer",
    "left_ear","right_ear",
    "mouth_left","mouth_right",
    "left_shoulder","right_shoulder",
    "left_elbow","right_elbow",
    "left_wrist","right_wrist",
    "left_pinky","right_pinky",
    "left_index","right_index",
    "left_thumb","right_thumb",
    "left_hip","right_hip",
    "left_knee","right_knee",
    "left_ankle","right_ankle",
    "left_heel","right_heel",
    "left_foot_index","right_foot_index"
];

const createPoseLandmarker = async () =>{
    // MediaPipe runtime(WASM) load
    const vision = await FilesetResolver.forVisionTasks( 
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );
    // Generate PoseLandmarker model
    poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath://Lite model
                "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
            delegate: delegate,
        },
        runningMode: runningMode,
        numPoses: numPoses,
        minPoseDetectionConfidence: minPoseDetectionConfidence,
        minPosePresenceConfidence: minPosePresenceConfidence,
        minTrackingConfidence: minTrackingConfidence,
        outputSegmentationMasks: outputSegmentationMasks,
        resultCallback: resultCallback,
    });
};

// MediaPipe runtime load & Generate PoseLandmarker model
createPoseLandmarker();

const image = document.getElementById('still-img');
const btn = document.querySelector('.btn');

if(btn){
    btn.addEventListener('click', handleClick);
};

async function handleClick(){
    
    // exception handling
    if(!poseLandmarker){
        console.log("PoseLandmarker is not ready yet!");
        return;
    };

    if(runningMode === 'VIDEO'){
        runningMode = "IMAGE";
        await poseLandmarker.setOptions({
            runningMode: 'IMAGE',
        });
    };

    // canvas cleanUp function
    // const allPrevCanvas = document.getElementsByClassName('canvas');

    // for (let i = allPrevCanvas.length - 1; i>=0; i--){
    //     const canvasToRemove = allPrevCanvas[i];
    //     canvasToRemove.parentNode.removeChild(canvasToRemove);
    // };

    const existingCanvas = image.parentNode.querySelector('#pose-canvas');
    if (existingCanvas) {
        existingCanvas.remove(); // 훨씬 간결한 삭제 방식
        console.log('canvas removed');
    }

    // draw canvas
    // callback은 스트리밍 결과를 계속 받기 위해 존재, IMAGE는 필요 없음.
    // poseLandmarker.detectForVideo(video, timestamp, callback);
    const result = poseLandmarker.detect(image);

    // sequencial streaming의 경우 아래 코드 callback으로 전달
    // createCanvas
    const canvas = document.createElement('canvas');

    // extract skeleton
    const skeletonData = result.landmarks[0]; //single person
    
    // skeleton labelling
    const labeledSkeleton = skeletonData.map((joint,index)=>({
        id:index,
        jointName:landmarkNames[index],
        x: joint.x,
        y: joint.y,
        z: joint.z,
        visibility: joint.visibility,
    }))

    console.log(JSON.stringify(labeledSkeleton, null, 4));


    
    canvas.id = 'pose-canvas'; //ID 부여(canvas cleanup 용)
    canvas.className = 'canvas';
    
    // set canvas style
    canvas.setAttribute('class','canvas');
    canvas.setAttribute('width',image.naturalWidth);
    canvas.setAttribute('height',image.naturalHeight);

    // set canvas element style
    canvas.style = 
        'left: 0px;' + 'top: 0px;' + 
        'width:' + image.width + 'px;' +
        'height:' + image.height + 'px;';

        image.parentNode.appendChild(canvas); 

    // canvas rendering (2d)
    const canvasCtx = canvas.getContext('2d');
    const drawingUtils = new DrawingUtils(canvasCtx);

    for (const landmark of result.landmarks){
        // draw landmarks
        drawingUtils.drawLandmarks(landmark, {
            radius: (data) => DrawingUtils.lerp(
                data.from.z, -0.15, 0.1, 5, 1
            )
        });

        // draw lines
        drawingUtils.drawConnectors(
            landmark, PoseLandmarker.POSE_CONNECTIONS
        );
    };
};