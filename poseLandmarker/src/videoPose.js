import {
    PoseLandmarker,
    FilesetResolver,
    DrawingUtils,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest";

const landmarkNames = [
    "nose",
    "left_eye_inner", "left_eye", "left_eye_outer",
    "right_eye_inner", "right_eye", "right_eye_outer",
    "left_ear", "right_ear",
    "mouth_left", "mouth_right",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_pinky", "right_pinky",
    "left_index", "right_index",
    "left_thumb", "right_thumb",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
    "left_foot_index", "right_foot_index",
];

const poseConnections = [
    [0, 1], [1, 2], [2, 3], [3, 7],
    [0, 4], [4, 5], [5, 6], [6, 8],
    [9, 10],
    [11, 12],
    [11, 13], [13, 15], [15, 17], [15, 19], [15, 21],
    [17, 19],
    [12, 14], [14, 16], [16, 18], [16, 20], [16, 22],
    [18, 20],
    [11, 23], [12, 24], [23, 24],
    [23, 25], [24, 26],
    [25, 27], [26, 28],
    [27, 29], [28, 30],
    [29, 31], [30, 32],
    [27, 31], [28, 32],
];

const video = document.getElementById("source-video");
const overlayCanvas = document.getElementById("video-overlay");
const extractButton = document.getElementById("extract-video-btn");
const playOverlayButton = document.getElementById("play-overlay-btn");
const downloadSkeletonButton = document.getElementById("download-skeleton-btn");
const statusText = document.getElementById("video-status");
const videoSourceSelect = document.getElementById("video-source-select");
const fpsInput = document.getElementById("video-fps");

let poseLandmarker;
let extractedFrames = [];
let extractedVideoInfo = null;
let overlayAnimationFrame = null;
let timestampCursorMs = 0;
let isOverlayPlaybackEnabled = false;
let extractButtonState = "idle";
let downloadButtonState = "idle";

const overlayContext = overlayCanvas ? overlayCanvas.getContext("2d") : null;
const drawingUtils = overlayContext ? new DrawingUtils(overlayContext) : null;

async function createPoseLandmarker() {
    const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm"
    );

    poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath:
                "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
            delegate: "GPU",
        },
        runningMode: "VIDEO",
        numPoses: 1,
        minPoseDetectionConfidence: 0.5,
        minPosePresenceConfidence: 0.5,
        minTrackingConfidence: 0.5,
        outputSegmentationMasks: false,
    });
}

const poseLandmarkerReady = createPoseLandmarker().catch((error) => {
    setStatus(`Pose model load failed: ${error.message}`);
    throw error;
});

if (video && videoSourceSelect) {
    videoSourceSelect.addEventListener("change", () => {
        disableOverlayPlayback();
        stopOverlayLoop();
        video.pause();
        video.currentTime = 0;
        video.src = videoSourceSelect.value;
        video.load();
        extractedFrames = [];
        extractedVideoInfo = null;
        clearOverlay();
        resetActionStates();
        updatePlaybackButtonLabel();
        syncActionState();
        setStatus("Video source updated. Run extraction again for this file.");
    });
}

if (extractButton) {
    extractButton.addEventListener("click", async () => {
        try {
            await extractVideoSkeletons();
        } catch (error) {
            console.error(error);
            setStatus(`Extraction failed: ${error.message}`);
            setExtractingState(false);
            syncActionState();
        }
    });
}

if (playOverlayButton) {
    playOverlayButton.addEventListener("click", async () => {
        try {
            await toggleOverlayPlayback();
        } catch (error) {
            console.error(error);
            setStatus(`Playback failed: ${error.message}`);
            updatePlaybackButtonLabel();
        }
    });
}

if (downloadSkeletonButton) {
    downloadSkeletonButton.addEventListener("click", async () => {
        try {
            setDownloadButtonState("active");
            downloadExtractedSkeletons();
            setDownloadButtonState("completed");
            syncActionState();
        } catch (error) {
            console.error(error);
            setDownloadButtonState("idle");
            syncActionState();
            setStatus(`Download failed: ${error.message}`);
        }
    });
}

if (fpsInput) {
    fpsInput.addEventListener("change", () => {
        extractedFrames = [];
        extractedVideoInfo = null;
        clearOverlay();
        resetActionStates();
        syncActionState();
        setStatus("FPS updated. Run extraction again to create a new skeleton bundle.");
    });
}

if (video) {
    video.addEventListener("loadedmetadata", syncOverlaySize);
    video.addEventListener("play", handleVideoPlay);
    video.addEventListener("pause", handleVideoPause);
    video.addEventListener("play", updatePlaybackButtonLabel);
    video.addEventListener("pause", updatePlaybackButtonLabel);
    video.addEventListener("ended", handlePlaybackEnded);
    video.addEventListener("seeked", drawFrameForCurrentTime);
}

window.addEventListener("resize", syncOverlaySize);

async function extractVideoSkeletons() {
    await poseLandmarkerReady;

    if (!video) {
        throw new Error("Video element not found.");
    }

    await ensureVideoMetadata(video);
    disableOverlayPlayback();
    video.pause();
    updatePlaybackButtonLabel();
    syncOverlaySize();
    clearOverlay();
    setDownloadButtonState("idle");
    setExtractingState(true);
    setStatus("Preparing video skeleton extraction...");
    extractedFrames = [];
    extractedVideoInfo = null;

    const fps = getTargetFps();
    const duration = video.duration;
    const totalFrames = Math.max(1, Math.floor(duration * fps));
    const processingVideo = await createProcessingVideo(video.currentSrc || video.src);
    const timestampBaseMs = timestampCursorMs;

    for (let frameIndex = 0; frameIndex <= totalFrames; frameIndex += 1) {
        const currentTime = Math.min(frameIndex / fps, Math.max(duration - 0.001, 0));
        await seekVideo(processingVideo, currentTime);
        const timestampMs = timestampBaseMs + Math.round(currentTime * 1000);

        const result = poseLandmarker.detectForVideo(processingVideo, timestampMs);
        const skeleton = formatSkeleton(result.landmarks?.[0] || []);

        extractedFrames.push({
            frameIndex,
            time: Number(currentTime.toFixed(6)),
            landmarks: skeleton,
        });

        if (frameIndex % 5 === 0 || frameIndex === totalFrames) {
            setStatus(`Extracting frame ${frameIndex + 1} / ${totalFrames + 1}`);
        }
    }

    timestampCursorMs = timestampBaseMs + Math.ceil(duration * 1000) + 1000;
    extractedVideoInfo = {
        videoSrc: video.currentSrc || video.src,
        fps,
        duration,
        createdAt: new Date().toISOString(),
    };

    clearOverlay();
    setExtractButtonState("completed");
    setDownloadButtonState("idle");
    setExtractingState(false);
    syncActionState();
    setStatus("Extraction complete. Play the video to view the skeleton overlay or download the JSON bundle.");
}

async function toggleOverlayPlayback() {
    if (!video) {
        throw new Error("Video element not found.");
    }

    if (!extractedFrames.length) {
        throw new Error("Extract skeleton data before playback.");
    }

    if (video.ended) {
        video.currentTime = 0;
        drawFrameForCurrentTime();
    }

    if (video.paused) {
        isOverlayPlaybackEnabled = true;
        await video.play();
        return;
    }

    if (isOverlayPlaybackEnabled) {
        disableOverlayPlayback();
    }
    video.pause();
}

async function createProcessingVideo(src) {
    const processingVideo = document.createElement("video");
    processingVideo.src = src;
    processingVideo.crossOrigin = "anonymous";
    processingVideo.muted = true;
    processingVideo.playsInline = true;
    processingVideo.preload = "auto";
    await ensureVideoMetadata(processingVideo);
    return processingVideo;
}

async function ensureVideoMetadata(targetVideo) {
    if (targetVideo.readyState >= 1) {
        return;
    }

    await new Promise((resolve, reject) => {
        const onLoaded = () => {
            cleanup();
            resolve();
        };
        const onError = () => {
            cleanup();
            reject(new Error("Video metadata could not be loaded."));
        };
        const cleanup = () => {
            targetVideo.removeEventListener("loadedmetadata", onLoaded);
            targetVideo.removeEventListener("error", onError);
        };

        targetVideo.addEventListener("loadedmetadata", onLoaded, { once: true });
        targetVideo.addEventListener("error", onError, { once: true });
    });
}

async function seekVideo(targetVideo, currentTime) {
    if (Math.abs(targetVideo.currentTime - currentTime) < 0.0005) {
        return;
    }

    await new Promise((resolve, reject) => {
        const onSeeked = () => {
            cleanup();
            resolve();
        };
        const onError = () => {
            cleanup();
            reject(new Error(`Seek failed at ${currentTime.toFixed(3)}s.`));
        };
        const cleanup = () => {
            targetVideo.removeEventListener("seeked", onSeeked);
            targetVideo.removeEventListener("error", onError);
        };

        targetVideo.addEventListener("seeked", onSeeked, { once: true });
        targetVideo.addEventListener("error", onError, { once: true });
        targetVideo.currentTime = currentTime;
    });
}

function formatSkeleton(landmarks) {
    return landmarkNames.map((jointName, index) => {
        const joint = landmarks[index];
        return {
            id: index,
            jointName,
            x: joint?.x ?? null,
            y: joint?.y ?? null,
            z: joint?.z ?? null,
            visibility: joint?.visibility ?? null,
        };
    });
}

function serializeJson(value, label) {
    const json = JSON.stringify(value);

    if (typeof json !== "string" || json.length === 0) {
        throw new Error(`${label}.json serialization produced no content.`);
    }

    return json;
}

function serializeFrames(frames) {
    return {
        v: 2,
        j: landmarkNames,
        f: frames.map((frame) => ({
            i: frame.frameIndex,
            t: roundNumber(frame.time, 4),
            p: frame.landmarks.map((joint) => [
                roundNullableNumber(joint.x, 5),
                roundNullableNumber(joint.y, 5),
                roundNullableNumber(joint.z, 5),
                roundNullableNumber(joint.visibility, 4),
            ]),
        })),
    };
}

function roundNullableNumber(value, decimals) {
    return typeof value === "number" ? roundNumber(value, decimals) : null;
}

function roundNumber(value, decimals) {
    const factor = 10 ** decimals;
    return Math.round(value * factor) / factor;
}

function getTargetFps() {
    const fps = Number(fpsInput?.value);
    return Number.isFinite(fps) && fps > 0 ? fps : 30;
}

function getVideoStem(videoSrc) {
    const normalized = videoSrc.split("?")[0];
    const fileName = normalized.split("/").pop() || "video";
    return fileName.replace(/\.[^.]+$/, "");
}

function createTimestampLabel() {
    const now = new Date();
    const parts = [
        now.getFullYear(),
        String(now.getMonth() + 1).padStart(2, "0"),
        String(now.getDate()).padStart(2, "0"),
        String(now.getHours()).padStart(2, "0"),
        String(now.getMinutes()).padStart(2, "0"),
        String(now.getSeconds()).padStart(2, "0"),
    ];
    return parts.join("");
}

function downloadExtractedSkeletons() {
    if (!extractedFrames.length || !extractedVideoInfo) {
        throw new Error("Extract skeleton data before downloading.");
    }

    const bundle = {
        metadata: {
            sourceVideo: extractedVideoInfo.videoSrc,
            fps: extractedVideoInfo.fps,
            duration: extractedVideoInfo.duration,
            frameCount: extractedFrames.length,
            storageFormat: "compact-single-file",
            schemaVersion: 2,
            frameFields: ["i", "t", "p"],
            pointFields: ["x", "y", "z", "v"],
            jointOrder: landmarkNames,
            createdAt: extractedVideoInfo.createdAt,
        },
        frames: serializeFrames(extractedFrames),
    };

    const fileName = `${getVideoStem(extractedVideoInfo.videoSrc)}-${createTimestampLabel()}.json`;
    const jsonText = serializeJson(bundle, "skeleton bundle");
    const blob = new Blob([jsonText], { type: "application/json" });
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = downloadUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(downloadUrl);

    setStatus(`Download started: ${fileName}`);
}

function syncOverlaySize() {
    if (!video || !overlayCanvas || !video.videoWidth || !video.videoHeight) {
        return;
    }

    overlayCanvas.width = video.videoWidth;
    overlayCanvas.height = video.videoHeight;
    drawFrameForCurrentTime();
}

function clearOverlay() {
    if (!overlayContext || !overlayCanvas) {
        return;
    }

    overlayContext.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

function drawOverlayFrame(labeledSkeleton) {
    if (!overlayContext || !overlayCanvas) {
        return;
    }

    clearOverlay();

    const visibleJoints = labeledSkeleton.filter(
        (joint) => typeof joint.x === "number" && typeof joint.y === "number"
    );

    if (!visibleJoints.length) {
        return;
    }

    overlayContext.lineWidth = 4;
    overlayContext.strokeStyle = "#6ee7ff";

    for (const [startIndex, endIndex] of poseConnections) {
        const start = labeledSkeleton[startIndex];
        const end = labeledSkeleton[endIndex];

        if (
            typeof start?.x !== "number" ||
            typeof start?.y !== "number" ||
            typeof end?.x !== "number" ||
            typeof end?.y !== "number"
        ) {
            continue;
        }

        overlayContext.beginPath();
        overlayContext.moveTo(start.x * overlayCanvas.width, start.y * overlayCanvas.height);
        overlayContext.lineTo(end.x * overlayCanvas.width, end.y * overlayCanvas.height);
        overlayContext.stroke();
    }

    for (const joint of visibleJoints) {
        const x = joint.x * overlayCanvas.width;
        const y = joint.y * overlayCanvas.height;
        const radius = drawingUtils
            ? DrawingUtils.lerp(joint.z ?? 0, -0.15, 0.1, 6, 2)
            : 4;

        overlayContext.beginPath();
        overlayContext.fillStyle = "#fff7ed";
        overlayContext.arc(x, y, radius, 0, Math.PI * 2);
        overlayContext.fill();

        overlayContext.lineWidth = 2;
        overlayContext.strokeStyle = "#f97316";
        overlayContext.stroke();
    }
}

function drawFrameForCurrentTime() {
    if (!video || !extractedFrames.length || !isOverlayPlaybackEnabled) {
        clearOverlay();
        return;
    }

    const targetTime = video.currentTime;
    const frame = findClosestFrame(targetTime);
    drawOverlayFrame(frame.landmarks);
}

function findClosestFrame(targetTime) {
    let closestFrame = extractedFrames[0];
    let minDiff = Math.abs(targetTime - closestFrame.time);

    for (let index = 1; index < extractedFrames.length; index += 1) {
        const frame = extractedFrames[index];
        const diff = Math.abs(targetTime - frame.time);

        if (diff < minDiff) {
            closestFrame = frame;
            minDiff = diff;
        }
    }

    return closestFrame;
}

function startOverlayLoop() {
    if (!isOverlayPlaybackEnabled) {
        clearOverlay();
        return;
    }

    stopOverlayLoop();

    const tick = () => {
        drawFrameForCurrentTime();
        if (!video.paused && !video.ended) {
            overlayAnimationFrame = window.requestAnimationFrame(tick);
        }
    };

    tick();
}

function stopOverlayLoop() {
    if (overlayAnimationFrame !== null) {
        window.cancelAnimationFrame(overlayAnimationFrame);
        overlayAnimationFrame = null;
    }
}

function handlePlaybackEnded() {
    stopOverlayLoop();
    if (isOverlayPlaybackEnabled) {
        drawFrameForCurrentTime();
        disableOverlayPlayback();
    } else {
        clearOverlay();
    }
    updatePlaybackButtonLabel();
}

function handleVideoPlay() {
    if (isOverlayPlaybackEnabled) {
        startOverlayLoop();
        return;
    }

    stopOverlayLoop();
    clearOverlay();
}

function handleVideoPause() {
    stopOverlayLoop();

    if (isOverlayPlaybackEnabled) {
        drawFrameForCurrentTime();
        return;
    }

    clearOverlay();
}

function disableOverlayPlayback() {
    isOverlayPlaybackEnabled = false;
    stopOverlayLoop();
    clearOverlay();
}

function setExtractingState(isExtracting) {
    if (isExtracting) {
        setExtractButtonState("active");
    } else if (extractButtonState === "active") {
        setExtractButtonState(extractedFrames.length ? "completed" : "idle");
    }

    if (playOverlayButton) {
        playOverlayButton.disabled = isExtracting || !extractedFrames.length;
    }

    const canDownload = extractedFrames.length && extractedVideoInfo && downloadButtonState !== "completed";
    if (downloadSkeletonButton) {
        downloadSkeletonButton.disabled = isExtracting || !canDownload;
    }
}

function syncActionState() {
    applyButtonVisualState(extractButton, extractButtonState, {
        idle: "Extract Video Skeleton",
        active: "Extracting...",
        completed: "Extracted",
    });
    applyButtonVisualState(downloadSkeletonButton, getDownloadVisualState(), {
        disabled: "Download Skeleton JSON",
        idle: "Download Skeleton JSON",
        active: "Downloading...",
        completed: "Downloaded",
    });
    setExtractingState(false);
    updatePlaybackButtonLabel();
}

function resetActionStates() {
    setExtractButtonState("idle");
    setDownloadButtonState("idle");
}

function setExtractButtonState(state) {
    extractButtonState = state;
    if (extractButton) {
        extractButton.disabled = state === "active" || state === "completed";
    }
}

function setDownloadButtonState(state) {
    downloadButtonState = state;
}

function applyButtonVisualState(button, state, labels) {
    if (!button) {
        return;
    }

    button.dataset.state = state === "idle" ? "primary" : state;
    button.textContent = labels[state];
    if (state === "completed") {
        button.disabled = true;
    }
}

function getDownloadVisualState() {
    if (downloadButtonState === "active" || downloadButtonState === "completed") {
        return downloadButtonState;
    }

    return extractedFrames.length && extractedVideoInfo ? "idle" : "disabled";
}

function updatePlaybackButtonLabel() {
    if (!playOverlayButton) {
        return;
    }

    playOverlayButton.textContent = video && isOverlayPlaybackEnabled && !video.paused && !video.ended
        ? "Pause Video + Skeleton"
        : "Play Video + Skeleton";
}

function setStatus(message) {
    if (statusText) {
        statusText.textContent = message;
    }
}

syncActionState();
