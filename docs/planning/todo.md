# Todo

- [ ] 개발 단계에서 MediaPipe 자세 추론의 속도와 정확도 지표를 확인할 수 있는 benchmark 체계를 추가한다.
  백엔드에서 프레임 추출, RGB 변환, 추론, 직렬화, 분석 단계별 시간을 구조화된 결과로 저장하고, `model_variant`, `delegate`, fallback 여부, pose detected ratio, visibility 같은 품질 지표를 함께 기록한다. 추후 일부 지표는 웹 UI에서 비교 차트와 요약 카드로 노출할 수 있게 API 응답/저장 구조를 함께 설계한다.
  세부 진행 기준은 아래와 같이 둔다.
  - benchmark 실행 단위를 `video_reader -> pose_inference -> analysis_pipeline` end-to-end 1회로 정의하고, 동일 입력 비디오에 대해 `model_variant`, `delegate`, 샘플링 조건별 반복 비교가 가능해야 한다.
  - 단계별 시간은 최소 `frame_extraction_ms`, `rgb_conversion_ms`, `inference_ms`, `serialization_ms`, `analysis_ms`, `total_elapsed_ms`로 저장하고, summary에는 평균/중앙값/p95와 전체 프레임 수 대비 단계별 누적 비중을 함께 둔다.
  - 품질 지표는 최소 `pose_detected_ratio`, `detected_frame_count`, `avg_visibility`, `min_visibility`, `low_visibility_frame_ratio`, `consecutive_missed_pose_max`, `analysis_success`를 포함하고, 추후 `world_landmarks`나 세그멘테이션 확장 시에도 같은 benchmark envelope를 재사용할 수 있게 한다.
  - 실행 메타데이터는 `benchmark_run_id`, `source_video_path`, `video_fingerprint`, `requested_delegate`, `actual_delegate`, `delegate_fallback_applied`, `model_variant`, `running_mode`, `frame_count`, `sample_interval_ms`, `started_at`, `completed_at` 정도를 기본 필드로 둔다.
  - 저장 구조는 `benchmark_runs` summary와 `benchmark_frame_metrics` 상세 레코드로 분리해, API에서는 기본적으로 summary를 반환하고 필요 시 frame-level 상세를 별도 조회하는 방식으로 설계한다.
  - API 응답은 웹 UI가 바로 비교 화면을 만들 수 있게 `run`, `timing_summary`, `quality_summary`, `comparison_tags` 블록으로 나누고, 프런트에서는 이를 기반으로 비교 차트, fallback 배지, 요약 카드, 품질 경고 카드를 노출할 수 있게 한다.
  - 1차 구현에서는 결과를 파일 또는 DB 한 곳에만 저장해도 되지만, 저장 스키마와 API 응답 shape는 동일 의미를 유지해 추후 저장소 교체 시 프런트와 서비스 계약이 깨지지 않게 한다.
- [ ] MediaPipe MVP 이후 확장 후보인 `world_landmarks`, `segmentation_mask`, 다중 영상 3D 융합을 후속 단계 작업으로 정리한다.
  현재 MVP는 `VIDEO + 2D landmarks only`로 유지하고, 확장 출력은 실제 소비자와 스키마 필요성이 생길 때 순차적으로 도입한다.
- [ ] 포즈 미검출 프레임 운영 정책을 후속 단계에서 보강한다.
  1차 버전에서는 `입력 프레임 처리 실패`는 작업 실패로 처리하고, `포즈 미검출`은 `pose_detected=False`인 정상 결과로 기록한다. 후속 단계에서는 미검출 프레임 비율, 연속 미검출 길이, 경고 임계치 도입 여부를 정리한다.
- [ ] 긴 영상 대응용 `PoseInferenceService.iter_infer()` 기반 확장 경로를 설계한다.
  `infer()` 중심 1차 구현 이후에 iterator 입력을 `skeleton_mapper`가 직접 받을지, 중간 accumulator를 둘지, chunk 단위 저장과 진행률 보고를 어떻게 붙일지 정리한다.
