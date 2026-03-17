import {
    DrawingUtils,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest";
import { poseConnections } from "./videoPose.constants.js";

export function createOverlayController({ video, overlayCanvas, getFrames, getIsPlaybackEnabled }) {
    const overlayContext = overlayCanvas ? overlayCanvas.getContext("2d") : null;
    const drawingUtils = overlayContext ? new DrawingUtils(overlayContext) : null;
    let overlayAnimationFrame = null;

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

    function findClosestFrame(targetTime) {
        const frames = getFrames();
        let closestFrame = frames[0];
        let minDiff = Math.abs(targetTime - closestFrame.time);

        for (let index = 1; index < frames.length; index += 1) {
            const frame = frames[index];
            const diff = Math.abs(targetTime - frame.time);

            if (diff < minDiff) {
                closestFrame = frame;
                minDiff = diff;
            }
        }

        return closestFrame;
    }

    function drawFrameForCurrentTime() {
        const frames = getFrames();
        if (!video || !frames.length || !getIsPlaybackEnabled()) {
            clearOverlay();
            return;
        }

        const frame = findClosestFrame(video.currentTime);
        drawOverlayFrame(frame.landmarks);
    }

    function syncOverlaySize() {
        if (!video || !overlayCanvas || !video.videoWidth || !video.videoHeight) {
            return;
        }

        overlayCanvas.width = video.videoWidth;
        overlayCanvas.height = video.videoHeight;
        drawFrameForCurrentTime();
    }

    function stopOverlayLoop() {
        if (overlayAnimationFrame !== null) {
            window.cancelAnimationFrame(overlayAnimationFrame);
            overlayAnimationFrame = null;
        }
    }

    function startOverlayLoop() {
        if (!getIsPlaybackEnabled()) {
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

    return {
        clearOverlay,
        drawFrameForCurrentTime,
        syncOverlaySize,
        startOverlayLoop,
        stopOverlayLoop,
    };
}
