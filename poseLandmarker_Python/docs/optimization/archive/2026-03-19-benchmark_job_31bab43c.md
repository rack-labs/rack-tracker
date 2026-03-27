# Benchmark Archive: 1st Test

## Metadata

- Benchmark Run ID: `benchmark_job_31bab43c`
- Date: `2026-03-19`
- Source Video: `src/video/backSquat.mp4`
- Video Fingerprint: `e59507e9b05cfe09`
- Requested Delegate: `GPU`
- Actual Delegate: `CPU`
- Delegate Fallback Applied: `true`
- Model Variant: `full`
- Running Mode: `VIDEO`
- Frame Count: `320`
- Sample Interval: `10.0ms`
- Started At: `2026-03-19T14:35:57.218763+00:00`
- Completed At: `2026-03-19T14:36:07.871872+00:00`

## Timing Summary

- Total Elapsed: `10653.101ms` (`10.65s`)
- Frame Extraction: `508.706ms` (`4.78%`)
- RGB Conversion: `171.979ms` (`1.61%`)
- Inference: `7964.166ms` (`74.76%`)
- Serialization: `50.882ms` (`0.48%`)
- Analysis: `0.103ms`

Inference detail:

- Average: `24.888ms/frame`
- Median: `23.337ms/frame`
- P95: `35.559ms/frame`

## Quality Summary

- Pose Detected Ratio: `1.0`
- Detected Frame Count: `320`
- Avg Visibility: `0.9803`
- Min Visibility: `0.8079`
- Low Visibility Frame Ratio: `0.0`
- Consecutive Missed Pose Max: `0`
- Analysis Success: `true`

## Interpretation

이 1차 테스트는 정확도 측면에서는 충분히 실사용 가능한 상태를 보여줍니다.

- 전 프레임에서 포즈 검출 성공
- visibility 품질이 높고 불안정 프레임 없음
- 추적 실패 구간 없음

반면 성능은 inference에 거의 완전히 묶여 있습니다.

- 전체 시간의 약 `74.76%`가 inference
- 나머지 구간은 최적화 우선순위가 낮음
- 현재 처리 속도는 입력 30fps와 거의 비슷한 수준이라 borderline real-time

핵심 문제는 GPU 요청이 실제로 적용되지 않았다는 점입니다.

- `requestedDelegate: GPU`
- `actualDelegate: CPU`
- `delegateFallbackApplied: true`

즉, 이 결과는 "MediaPipe full 모델의 성능 한계"라기보다 "GPU 구성 실패로 CPU fallback 상태에서 측정된 기준선"으로 봐야 합니다.

## Business View

- Accuracy: very high
- Speed: borderline real-time
- Scalability: low

짧은 영상 단건 처리에는 충분하지만, 긴 영상이나 동시 요청에서는 병목이 빠르게 누적될 가능성이 높습니다.

## Action Items

1. GPU delegate 문제를 먼저 해결하거나 GPU 가능한 다른 추론 스택으로 전환
2. `samplingIntervalMs`를 `33ms` 또는 `50ms`로 조정해 연산량 감축
3. `full`과 `lite` 모델 전략 분리
4. API와 worker를 분리해 동시성 대응

## Source of Truth

- Summary JSON: [benchmark_job_31bab43c.summary.json](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\tmp\benchmarks\benchmark_job_31bab43c.summary.json)
- Frame Metrics JSON: [benchmark_job_31bab43c.frames.json](C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\tmp\benchmarks\benchmark_job_31bab43c.frames.json)
