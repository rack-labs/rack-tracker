export function createVideoPoseUI({
    extractButton,
    playOverlayButton,
    downloadSkeletonButton,
    statusText,
    getFrames,
    getVideoInfo,
    getIsPlaybackEnabled,
    getExtractButtonState,
    getDownloadButtonState,
    setExtractButtonState,
}) {
    function setStatus(message) {
        if (statusText) {
            statusText.textContent = message;
        }
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
        const downloadButtonState = getDownloadButtonState();
        if (downloadButtonState === "active" || downloadButtonState === "completed") {
            return downloadButtonState;
        }

        return getFrames().length && getVideoInfo() ? "idle" : "disabled";
    }

    function updatePlaybackButtonLabel(video) {
        if (!playOverlayButton) {
            return;
        }

        playOverlayButton.textContent = video && getIsPlaybackEnabled() && !video.paused && !video.ended
            ? "Pause Video + Skeleton"
            : "Play Video + Skeleton";
    }

    function setExtractingState(isExtracting) {
        if (isExtracting) {
            setExtractButtonState("active");
        } else if (getExtractButtonState() === "active") {
            setExtractButtonState(getFrames().length ? "completed" : "idle");
        }

        if (playOverlayButton) {
            playOverlayButton.disabled = isExtracting || !getFrames().length;
        }

        const canDownload = getFrames().length && getVideoInfo() && getDownloadButtonState() !== "completed";
        if (downloadSkeletonButton) {
            downloadSkeletonButton.disabled = isExtracting || !canDownload;
        }
    }

    function syncActionState(video) {
        applyButtonVisualState(extractButton, getExtractButtonState(), {
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
        updatePlaybackButtonLabel(video);
    }

    return {
        setStatus,
        updatePlaybackButtonLabel,
        setExtractingState,
        syncActionState,
    };
}
