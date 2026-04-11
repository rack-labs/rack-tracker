import { formatSkeleton } from "./videoPose.data.js";

export async function ensureVideoMetadata(targetVideo) {
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

export async function createProcessingVideo(src) {
    const processingVideo = document.createElement("video");
    processingVideo.src = src;
    processingVideo.crossOrigin = "anonymous";
    processingVideo.muted = true;
    processingVideo.playsInline = true;
    processingVideo.preload = "auto";
    await ensureVideoMetadata(processingVideo);
    return processingVideo;
}

export async function seekVideo(targetVideo, currentTime) {
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

export async function extractVideoSkeletons({
    poseLandmarker,
    video,
    fps,
    timestampBaseMs,
    onProgress,
}) {
    await ensureVideoMetadata(video);

    const duration = video.duration;
    const totalFrames = Math.max(1, Math.floor(duration * fps));
    const processingVideo = await createProcessingVideo(video.currentSrc || video.src);
    const frames = [];

    for (let frameIndex = 0; frameIndex <= totalFrames; frameIndex += 1) {
        const currentTime = Math.min(frameIndex / fps, Math.max(duration - 0.001, 0));
        await seekVideo(processingVideo, currentTime);
        const timestampMs = timestampBaseMs + Math.round(currentTime * 1000);

        const result = poseLandmarker.detectForVideo(processingVideo, timestampMs);
        const skeleton = formatSkeleton(result.landmarks?.[0] || []);

        frames.push({
            frameIndex,
            time: Number(currentTime.toFixed(6)),
            landmarks: skeleton,
        });

        if (onProgress && (frameIndex % 5 === 0 || frameIndex === totalFrames)) {
            onProgress({ frameIndex, totalFrames });
        }
    }

    return {
        frames,
        videoInfo: {
            videoSrc: video.currentSrc || video.src,
            fps,
            duration,
            createdAt: new Date().toISOString(),
        },
        nextTimestampCursorMs: timestampBaseMs + Math.ceil(duration * 1000) + 1000,
    };
}
