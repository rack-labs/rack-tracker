# Todo

- [ ] 개발 단계에서 MediaPipe 자세 추론의 속도와 정확도 지표를 확인할 수 있는 benchmark 체계를 추가한다.
  백엔드에서 프레임 추출, RGB 변환, 추론, 직렬화, 분석 단계별 시간을 구조화된 결과로 저장하고, `model_variant`, `delegate`, fallback 여부, pose detected ratio, visibility 같은 품질 지표를 함께 기록한다. 추후 일부 지표는 웹 UI에서 비교 차트와 요약 카드로 노출할 수 있게 API 응답/저장 구조를 함께 설계한다.
- [ ] MediaPipe MVP 이후 확장 후보인 `world_landmarks`, `segmentation_mask`, 다중 영상 3D 융합을 후속 단계 작업으로 정리한다.
  현재 MVP는 `VIDEO + 2D landmarks only`로 유지하고, 확장 출력은 실제 소비자와 스키마 필요성이 생길 때 순차적으로 도입한다.
- [ ] 포즈 미검출 프레임 운영 정책을 후속 단계에서 보강한다.
  1차 버전에서는 `입력 프레임 처리 실패`는 작업 실패로 처리하고, `포즈 미검출`은 `pose_detected=False`인 정상 결과로 기록한다. 후속 단계에서는 미검출 프레임 비율, 연속 미검출 길이, 경고 임계치 도입 여부를 정리한다.
- [ ] 긴 영상 대응용 `PoseInferenceService.iter_infer()` 기반 확장 경로를 설계한다.
  `infer()` 중심 1차 구현 이후에 iterator 입력을 `skeleton_mapper`가 직접 받을지, 중간 accumulator를 둘지, chunk 단위 저장과 진행률 보고를 어떻게 붙일지 정리한다.
