import { ImageSegmenter, FilesetResolver }
from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest";

let imageSegmenter;

async function createImageSegmenter(){
    const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );
    imageSegmenter = await ImageSegmenter.createFromOptions(vision, {
        baseOptions:{
            modelAssetPath: //
            "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/1/selfie_segmenter.tflite",
            delegate: 'GPU',
        },
        runningMode: 'IMAGE',
        outputCategoryMask: true,
        outputConfidenceMasks: false,
    });
    console.log("ImageSegmenter loaded");
}

createImageSegmenter();