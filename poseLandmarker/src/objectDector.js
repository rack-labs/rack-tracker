import { ObjectDetector, FilesetResolver }
from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest";

let objectDetector;

async function createObjectDector(){
    const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );
    objectDetector = await ObjectDetector.createFromOptions(vision,{
        baseOptions:{
            modelAssetPath: // efficientdet_lite0 TensorFlow Lite
            "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite",
            delegate: 'GPU', //모바일에서는 cpu?
        },
        runningMode: 'IMAGE', //or VIDEO
        scoreThreshold: 0.5,
    });
    console.log('ObjectDector loaded.');
};

createObjectDector();