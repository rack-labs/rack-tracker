import { landmarkNames } from "./videoPose.constants.js";
import {
    serializeJson,
    serializeFrames,
    getVideoStem,
    createTimestampLabel,
} from "./videoPose.data.js";
import { createPoseLandmarker } from "./videoPose.model.js";
import { extractVideoSkeletons } from "./videoPose.extractor.js";
import { createOverlayController } from "./videoPose.overlay.js";
import { createVideoPoseUI } from "./videoPose.ui.js";

const video = document.getElementById("source-video");
const overlayCanvas = document.getElementById("video-overlay");
const extractButton = document.getElementById("extract-video-btn");
const playOverlayButton = document.getElementById("play-overlay-btn");
const downloadSkeletonButton = document.getElementById("download-skeleton-btn");
const statusText = document.getElementById("video-status");
const videoSourceSelect = document.getElementById("video-source-select");
const fpsInput = document.getElementById("video-fps");

const state = {
    poseLandmarker: null,
    extractedFrames: [],
    extractedVideoInfo: null,
    timestampCursorMs: 0,
    isOverlayPlaybackEnabled: false,
    extractButtonState: "idle",
    downloadButtonState: "idle",
};

const overlay = createOverlayController({
    video,
    overlayCanvas,
    getFrames: () => state.extractedFrames,
    getIsPlaybackEnabled: () => state.isOverlayPlaybackEnabled,
});

const ui = createVideoPoseUI({
    extractButton,
    playOverlayButton,
    downloadSkeletonButton,
    statusText,
    getFrames: () => state.extractedFrames,
    getVideoInfo: () => state.extractedVideoInfo,
    getIsPlaybackEnabled: () => state.isOverlayPlaybackEnabled,
    getExtractButtonState: () => state.extractButtonState,
    getDownloadButtonState: () => state.downloadButtonState,
    setExtractButtonState: (nextState) => {
        state.extractButtonState = nextState;
        if (extractButton) {
            extractButton.disabled = nextState === "active" || nextState === "completed";
        }
    },
});

const poseLandmarkerReady = createPoseLandmarker()
    .then((poseLandmarker) => {
        state.poseLandmarker = poseLandmarker;
    })
    .catch((error) => {
        ui.setStatus(`Pose model load failed: ${error.message}`);
        throw error;
    });

if (video && videoSourceSelect) {
    videoSourceSelect.addEventListener("change", () => {
        disableOverlayPlayback();
        overlay.stopOverlayLoop();
        video.pause();
        video.currentTime = 0;
        video.src = videoSourceSelect.value;
        video.load();
        resetExtractedData();
        resetActionStates();
        ui.updatePlaybackButtonLabel(video);
        ui.syncActionState(video);
        ui.setStatus("Video source updated. Run extraction again for this file.");
    });
}

if (extractButton) {
    extractButton.addEventListener("click", async () => {
        try {
            await handleExtractVideoSkeletons();
        } catch (error) {
            console.error(error);
            ui.setStatus(`Extraction failed: ${error.message}`);
            ui.setExtractingState(false);
            ui.syncActionState(video);
        }
    });
}

if (playOverlayButton) {
    playOverlayButton.addEventListener("click", async () => {
        try {
            await toggleOverlayPlayback();
        } catch (error) {
            console.error(error);
            ui.setStatus(`Playback failed: ${error.message}`);
            ui.updatePlaybackButtonLabel(video);
        }
    });
}

if (downloadSkeletonButton) {
    downloadSkeletonButton.addEventListener("click", async () => {
        try {
            state.downloadButtonState = "active";
            downloadExtractedSkeletons();
            state.downloadButtonState = "completed";
            ui.syncActionState(video);
        } catch (error) {
            console.error(error);
            state.downloadButtonState = "idle";
            ui.syncActionState(video);
            ui.setStatus(`Download failed: ${error.message}`);
        }
    });
}

if (fpsInput) {
    fpsInput.addEventListener("change", () => {
        resetExtractedData();
        resetActionStates();
        ui.syncActionState(video);
        ui.setStatus("FPS updated. Run extraction again to create a new skeleton bundle.");
    });
}

if (video) {
    video.addEventListener("loadedmetadata", overlay.syncOverlaySize);
    video.addEventListener("play", handleVideoPlay);
    video.addEventListener("pause", handleVideoPause);
    video.addEventListener("play", () => ui.updatePlaybackButtonLabel(video));
    video.addEventListener("pause", () => ui.updatePlaybackButtonLabel(video));
    video.addEventListener("ended", handlePlaybackEnded);
    video.addEventListener("seeked", overlay.drawFrameForCurrentTime);
}

window.addEventListener("resize", overlay.syncOverlaySize);

async function handleExtractVideoSkeletons() {
    await poseLandmarkerReady;

    if (!video || !state.poseLandmarker) {
        throw new Error("Video element not found.");
    }

    disableOverlayPlayback();
    video.pause();
    ui.updatePlaybackButtonLabel(video);
    overlay.syncOverlaySize();
    overlay.clearOverlay();
    state.downloadButtonState = "idle";
    ui.setExtractingState(true);
    ui.setStatus("Preparing video skeleton extraction...");
    resetExtractedData();

    const result = await extractVideoSkeletons({
        poseLandmarker: state.poseLandmarker,
        video,
        fps: getTargetFps(),
        timestampBaseMs: state.timestampCursorMs,
        onProgress: ({ frameIndex, totalFrames }) => {
            ui.setStatus(`Extracting frame ${frameIndex + 1} / ${totalFrames + 1}`);
        },
    });

    state.extractedFrames = result.frames;
    state.extractedVideoInfo = result.videoInfo;
    state.timestampCursorMs = result.nextTimestampCursorMs;

    overlay.clearOverlay();
    state.extractButtonState = "completed";
    state.downloadButtonState = "idle";
    ui.setExtractingState(false);
    ui.syncActionState(video);
    ui.setStatus("Extraction complete. Play the video to view the skeleton overlay or download the JSON bundle.");
}

async function toggleOverlayPlayback() {
    if (!video) {
        throw new Error("Video element not found.");
    }

    if (!state.extractedFrames.length) {
        throw new Error("Extract skeleton data before playback.");
    }

    if (video.ended) {
        video.currentTime = 0;
        overlay.drawFrameForCurrentTime();
    }

    if (video.paused) {
        state.isOverlayPlaybackEnabled = true;
        await video.play();
        return;
    }

    if (state.isOverlayPlaybackEnabled) {
        disableOverlayPlayback();
    }
    video.pause();
}

function getTargetFps() {
    const fps = Number(fpsInput?.value);
    return Number.isFinite(fps) && fps > 0 ? fps : 30;
}

function downloadExtractedSkeletons() {
    if (!state.extractedFrames.length || !state.extractedVideoInfo) {
        throw new Error("Extract skeleton data before downloading.");
    }

    const bundle = {
        metadata: {
            sourceVideo: state.extractedVideoInfo.videoSrc,
            fps: state.extractedVideoInfo.fps,
            duration: state.extractedVideoInfo.duration,
            frameCount: state.extractedFrames.length,
            storageFormat: "compact-single-file",
            schemaVersion: 2,
            frameFields: ["i", "t", "p"],
            pointFields: ["x", "y", "z", "v"],
            jointOrder: landmarkNames,
            createdAt: state.extractedVideoInfo.createdAt,
        },
        frames: serializeFrames(state.extractedFrames),
    };

    const fileName = `${getVideoStem(state.extractedVideoInfo.videoSrc)}-${createTimestampLabel()}.json`;
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

    ui.setStatus(`Download started: ${fileName}`);
}

function handlePlaybackEnded() {
    overlay.stopOverlayLoop();
    if (state.isOverlayPlaybackEnabled) {
        overlay.drawFrameForCurrentTime();
        disableOverlayPlayback();
    } else {
        overlay.clearOverlay();
    }
    ui.updatePlaybackButtonLabel(video);
}

function handleVideoPlay() {
    if (state.isOverlayPlaybackEnabled) {
        overlay.startOverlayLoop();
        return;
    }

    overlay.stopOverlayLoop();
    overlay.clearOverlay();
}

function handleVideoPause() {
    overlay.stopOverlayLoop();

    if (state.isOverlayPlaybackEnabled) {
        overlay.drawFrameForCurrentTime();
        return;
    }

    overlay.clearOverlay();
}

function disableOverlayPlayback() {
    state.isOverlayPlaybackEnabled = false;
    overlay.stopOverlayLoop();
    overlay.clearOverlay();
}

function resetExtractedData() {
    state.extractedFrames = [];
    state.extractedVideoInfo = null;
    overlay.clearOverlay();
}

function resetActionStates() {
    state.extractButtonState = "idle";
    state.downloadButtonState = "idle";
}

ui.syncActionState(video);
