import { landmarkNames } from "./videoPose.constants.js";

export function formatSkeleton(landmarks) {
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

export function serializeJson(value, label) {
    const json = JSON.stringify(value);

    if (typeof json !== "string" || json.length === 0) {
        throw new Error(`${label}.json serialization produced no content.`);
    }

    return json;
}

export function serializeFrames(frames) {
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

export function roundNullableNumber(value, decimals) {
    return typeof value === "number" ? roundNumber(value, decimals) : null;
}

export function roundNumber(value, decimals) {
    const factor = 10 ** decimals;
    return Math.round(value * factor) / factor;
}

export function getVideoStem(videoSrc) {
    const normalized = videoSrc.split("?")[0];
    const fileName = normalized.split("/").pop() || "video";
    return fileName.replace(/\.[^.]+$/, "");
}

export function createTimestampLabel() {
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
