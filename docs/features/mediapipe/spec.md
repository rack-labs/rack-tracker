# MediaPipe 기반 포즈 랜드마커 기능 명세

> 문서 동기화 강제 프롬프트
>
> 이 문서를 수정하는 AI 또는 작성자는 반드시 아래 짝 문서를 함께 확인해야 한다.
>
> - `docs/features/mediapipe/architecture.md`
>
> 규칙:
>
> - 명세가 바뀌면 아키텍처 문서도 즉시 확인하고, 불일치가 있으면 함께 수정한다.
> - 아키텍처가 바뀌어 명세 설명과 충돌하면, 이 문서도 즉시 수정한다.
> - 둘 중 하나만 수정하고 다른 문서를 방치하지 않는다.
> - 특히 아래 항목이 바뀌면 상대 문서를 반드시 같이 수정한다.
>   - 입력 포트
>   - 출력 포트
>   - 데이터 흐름
>   - 옵션 이름
>   - 목업 데이터 정책
>   - 예외 정책
>   - 성능 관련 옵션 또는 권고
>
> 실행 지시:
>
> - 이 문서를 수정한 뒤에는 반드시 짝 문서를 다시 읽고, 동일한 변경이 반영되어야 하는지 점검하라.
> - 필요하면 두 문서를 같은 커밋 또는 같은 작업 단위에서 함께 수정하라.

## 1. 이 문서는 무엇인가

이 문서는 `MediaPipe 기반 포즈 랜드마커 기능`을 비개발자도 이해할 수 있게 설명하는 문서다.

쉽게 말하면 이 기능은:

- 운동 영상을 받아서
- 사람 몸의 주요 관절 위치를 찾아내고
- 그 결과를 다음 분석 단계가 쓰기 쉬운 데이터로 정리해 주는 장치다.

가전제품으로 비유하면, 이 기능은 "영상 속 사람 자세를 읽어서 관절 좌표표를 뽑아 주는 기계"라고 보면 된다.

아래 설명은 두 층으로 적는다.

- 쉬운 설명: 비개발자도 이해할 수 있는 비유 중심 설명
- 아키텍처 연동 설명: `architecture.md`나 설계 문서를 수정할 때 바로 연결해서 볼 수 있는 설명

---

## 2. 이 기능을 가전제품으로 보면

### 쉬운 설명

이 기능은 "자세 판독기"다.

- 입력구에 이미지나 비디오 프레임이 들어온다.
- 기계 안에서 사람의 몸을 찾는다.
- 어깨, 골반, 무릎 같은 주요 지점을 계산한다.
- 계산된 지점을 정리해서 밖으로 내보낸다.

이때 밖으로 나가는 결과는 보통 아래처럼 묶인다.

- 프레임별 포즈 감지 여부
- 관절 좌표 목록
- 프레임 번호와 시간 정보
- 후속 분석에 필요한 구조화된 JSON 데이터

즉, 이 기계는 "영상 장면을 사람 자세 데이터로 바꿔 주는 중간 장치"다.

### 아키텍처 연동 설명

시스템 구조상 이 기능은 아래 위치에 해당한다.

- 입력 쪽:
  - `service/video_reader.py`
  - 또는 이후 이미지 입력 경로
- 중간 처리:
  - `service/pose_inference.py`
- 외부 라이브러리 연결부:
  - `adapter/mediapipe_adapter.py`
- 출력 연결 대상:
  - `service/skeleton_mapper.py`
  - `service/analysis_pipeline.py`
  - `service/llm_feedback.py`

즉, 이 기능은 전체 백엔드에서 "프레임을 실제 자세 데이터로 바꾸는 핵심 추론 장치"다.

---

## 3. 입력 포트와 출력 포트

### 3.1 입력 포트

### 쉬운 설명

이 기계의 입력 포트는 아래와 같다.

1. 분석할 프레임 이미지
2. 각 프레임의 번호와 시간 정보
3. 사용할 MediaPipe 모델 파일 경로
4. 몇 명까지 감지할지, 신뢰도 기준을 얼마나 둘지 정하는 옵션
5. GPU를 우선 사용할지, CPU로 자동 전환할지 정하는 실행 정책

현재 프로젝트 기준으로는 프론트와 백엔드가 완전히 연결되기 전까지 실제 업로드 파일 대신 아래 목업 비디오에서 뽑은 프레임이 기본 입력이 된다.

- `poseLandmarker_Python/src/video/backSquat.mp4`

즉, 지금은 사용자가 실제 영상을 넣지 않아도 내부 샘플 프레임으로 동작 흐름을 확인할 수 있다.

### 아키텍처 연동 설명

현재 입력 관련 기준은 아래와 같다.

- API 입력 진입점: `poseLandmarker_Python/controller/jobs.py`
- 작업 오케스트레이션: `poseLandmarker_Python/service/job_manager.py`
- 프레임 공급 계층: `poseLandmarker_Python/service/video_reader.py`
- 임시 기본 입력 경로: `poseLandmarker_Python/config/config.py`의 `MOCK_VIDEO_PATH`
- 현재 목업 파일:
  - `poseLandmarker_Python/src/video/backSquat.mp4`

현재 `JobManager`는 프레임 추출 결과를 `PoseInferenceService.infer()`에 전달하는 구조다.

---

### 3.2 출력 포트

### 쉬운 설명

이 기계의 출력 포트는 아래와 같다.

1. 프레임별 포즈 감지 성공 여부
2. 2D 관절 좌표 목록
3. 각 좌표의 가시성 또는 신뢰도 정보
4. 프레임 번호
5. 프레임 시간 정보

즉, "사람이 있었다"는 판정만 나오는 것이 아니라, "어느 관절이 화면 어디에 있었는지"까지 같이 나온다.

### 아키텍처 연동 설명

출력은 개념적으로 아래 두 갈래다.

- 추론 직접 출력:
  - `PoseInferenceService.infer()`의 프레임별 결과 목록
- 후속 매핑 출력:
  - `SkeletonMapperService.map_landmarks()`가 만드는 `skeleton.frames`
  - `skeleton.videoInfo`

현재 스텁 구현 기준 결과 항목은 아래 구조에 가깝다.

- `frameIndex`
- `timestampMs`
- `poseDetected`
- `landmarks`

현재 MVP v1 범위에서는 이 `landmarks`를 2D 스켈레톤 출력으로 본다.

---

## 4. 이 기능이 실제로 하는 일

### 쉬운 설명

이 기능은 영상 장면을 그냥 보기 좋게 표시하는 장치가 아니다.

핵심은 각 장면에서 사람의 자세를 읽어 숫자 데이터로 바꾸는 것이다.

보통은 아래 일을 한다.

- 프레임 이미지 받기
- 사람 자세 찾기
- 주요 관절 좌표 계산하기
- 결과를 JSON 형태로 정리하기
- 다음 분석 장치로 넘기기

즉, "그림을 본다"가 아니라 "그림을 읽어서 관절 데이터로 바꾼다"가 핵심이다.

### 아키텍처 연동 설명

이 규칙은 MediaPipe Pose Landmarker 옵션과 서비스 경계 기준으로 정리된다.

- `running_mode`
- `num_poses`
- `min_pose_detection_confidence`
- `min_pose_presence_confidence`
- `min_tracking_confidence`
- `delegate`
- 필요 시:
  - `output_segmentation_masks`

권장 기본값은 아래와 같다.

- 기본 실행: GPU 가속
- fallback: GPU 초기화 실패 시 CPU 자동 전환
- MVP v1 출력 범위: 2D 스켈레톤만 반환

이 옵션들은 주로 `adapter/mediapipe_adapter.py`가 MediaPipe 객체 생성 시 해석하고, `service/pose_inference.py`는 프레임 단위 추론 흐름과 결과 정리를 담당하는 형태가 바람직하다.

---

## 5. 입력된 데이터가 지나가는 길

### 쉬운 설명

이 기능 안에서 데이터는 아래 길을 따라 이동한다.

1. 영상 또는 프레임이 들어온다.
2. 프레임 추출 장치가 분석할 장면을 준비한다.
3. 자세 판독 장치가 각 장면을 읽는다.
4. 관절 좌표를 계산한다.
5. 계산된 결과를 프레임 정보와 묶는다.
6. 정리된 결과를 분석기로 넘긴다.

이 흐름은 공장 조립라인처럼 생각하면 쉽다.

- 입고: 프레임 입력
- 판독: MediaPipe 추론
- 정리: 결과 구조화
- 출고: 분석 파이프라인 전달

### 아키텍처 연동 설명

권장 내부 경로는 아래와 같다.

1. `controller/jobs.py`
   - 요청을 받는다.
2. `service/job_manager.py`
   - 작업을 생성하고 상태를 관리한다.
3. `service/video_reader.py`
   - 분석할 프레임을 공급한다.
4. `service/pose_inference.py`
   - 프레임을 순회하며 포즈 추론을 수행한다.
5. `adapter/mediapipe_adapter.py`
   - MediaPipe Pose Landmarker 인스턴스를 만든다.
6. `service/skeleton_mapper.py`
   - 추론 결과를 스켈레톤 구조로 정리한다.
7. `service/analysis_pipeline.py`
   - 정리된 자세 결과를 운동 분석에 사용한다.

즉, `service/pose_inference.py`는 추론 제어부, `adapter/mediapipe_adapter.py`는 MediaPipe와 직접 연결되는 기계 내부 엔진이라고 보면 된다.

---

## 6. 입력 데이터는 어떤 형식으로 들어오고, 중간에 어떻게 바뀌는가

### 쉬운 설명

처음에는 "프레임 이미지" 상태다.

그다음에는 "MediaPipe가 읽을 수 있는 이미지 객체" 상태가 된다.

그다음에는 "관절 좌표와 감지 여부가 붙은 추론 결과" 상태가 된다.

그다음에는 "분석용 스켈레톤 데이터" 상태가 된다.

즉, 데이터는 아래처럼 변한다.

- 프레임 이미지
- MediaPipe 입력 이미지
- 포즈 랜드마커 결과
- 프레임별 랜드마크 목록
- 스켈레톤 JSON

### 아키텍처 연동 설명

형식 변화는 아래처럼 보는 것이 좋다.

1. `ExtractedFrame`
   - 예: `index`, `timestamp_ms`, `image`
2. MediaPipe 입력 객체
   - 예: `mp.Image`
3. Pose Landmarker 결과
   - 예: `PoseLandmarkerResult`
4. 직렬화된 프레임 결과
   - 예: `{"frameIndex": ..., "landmarks": [...]}`
5. 스켈레톤 구조
   - 예: `skeleton.frames`, `skeleton.videoInfo`

즉, 이 기능의 핵심 형식 변화는 "프레임 객체 -> MediaPipe 입력 -> 랜드마크 결과 -> 분석용 JSON 구조"다.

---

## 7. 포트별 상세 설명

### 7.1 프레임 입력 포트

### 쉬운 설명

여기에 들어오는 것은 분석 대상 장면이다.

현재는 주로 비디오에서 뽑아 둔 프레임이 들어온다.

나중에는 아래 둘 다 가능해진다.

- 사용자가 올린 비디오에서 나온 프레임
- 사용자가 직접 올린 단일 이미지

### 아키텍처 연동 설명

현재 상태:

- `JobManager`가 `VideoReaderService` 결과를 바로 추론 입력으로 사용한다.
- `PoseInferenceService.infer()`는 `list[ExtractedFrame]`를 받는다.

향후 연결 완료 시 바뀔 부분:

- 단일 이미지 전용 추론 경로 추가
- 스트리밍 또는 비동기 프레임 처리 추가

---

### 7.2 모델 설정 포트

### 쉬운 설명

여기는 "어떤 판독기를 쓸지" 정하는 포트다.

예를 들어:

- 어떤 모델 파일을 쓸지
- `lite`, `full`, `heavy` 중 어떤 급을 쓸지
- 한 번에 몇 사람까지 찾을지
- 얼마나 확실해야 찾았다고 볼지

이 조절값을 잘 잡으면 정확도와 속도 균형을 바꿀 수 있다.

현재 MediaPipe Pose Landmarker 계열에서 실무적으로 고려할 모델은 보통 아래 3가지다.

- `Lite`
  - 가장 빠르다.
  - 정확도는 가장 낮은 편이다.
  - 실시간성이 가장 중요할 때 적합하다.
- `Full`
  - 속도와 정확도의 균형형이다.
  - 백엔드 기본값으로 가장 무난하다.
- `Heavy`
  - 가장 정확한 편이다.
  - 가장 무겁고 CPU fallback 시 부담이 크다.
  - 품질 우선 배치 분석에 적합하다.

### 아키텍처 연동 설명

이 포트는 MediaPipe 옵션 필드에 대응한다.

- `base_options.model_asset_path`
- `model_variant`
- `running_mode`
- `num_poses`
- `min_pose_detection_confidence`
- `min_pose_presence_confidence`
- `min_tracking_confidence`
- `delegate`

정책 결정은 `service/pose_inference.py`, 실제 Landmarker 생성은 `adapter/mediapipe_adapter.py`가 맡는 분리가 적절하다.

권장 정책:

- 기본 모델은 `Full`로 둔다.
- `delegate="GPU"`를 기본값으로 둔다.
- GPU 초기화 실패 시 자동으로 CPU fallback을 시도한다.
- fallback 여부는 로그나 메타데이터로 남겨 운영자가 확인할 수 있게 한다.

모델 선택 기준:

- 실시간 우선: `Lite`
- 기본 운영: `Full`
- 정확도 우선 배치 분석: `Heavy`

---

### 7.3 추론 실행 포트

### 쉬운 설명

이 포트는 "한 장씩 읽을지, 비디오 흐름으로 읽을지"를 정하는 포트다.

- 이미지 모드
- 비디오 모드
- 실시간 스트림 모드

현재 백엔드 흐름에서는 보통 비디오 모드가 가장 자연스럽다.

### 아키텍처 연동 설명

관련 개념은 아래와 같다.

- `detect()`
- `detect_for_video()`
- `detect_async()`

현재 프로젝트 구조에서는 `detect_for_video()` 중심 설계가 가장 잘 맞는다.

이유는 아래와 같다.

- 프레임마다 `timestamp_ms`가 이미 존재한다.
- `job_manager.py`의 배치 처리 흐름과 맞다.
- 후속 `analysis_pipeline.py`가 시간축 정보를 바로 활용할 수 있다.

---

### 7.4 결과 직렬화 포트

### 쉬운 설명

이 포트는 "찾아낸 자세를 다른 장치도 읽을 수 있게 정리하는 포트"다.

- 관절 이름 붙이기
- 좌표를 JSON으로 정리하기
- 프레임 정보와 함께 묶기

이 정리 단계가 있어야 분석기와 피드백 생성기가 쉽게 이어 붙는다.

### 아키텍처 연동 설명

현재 스텁 기준 관련 계층은 아래와 같다.

- `service/pose_inference.py`
  - 프레임별 결과 생성
- `service/skeleton_mapper.py`
  - `videoInfo`, `frames`, `nextTimestampCursorMs` 조립

향후 실제 MediaPipe 연동 시에도 이 두 단계 분리를 유지하는 것이 좋다.

현재 범위에서는 `service/pose_inference.py`가 2D 좌표만 직렬화한다고 보면 된다.

---

## 8. 이 기능이 내보내는 결과물의 모양

### 쉬운 설명

결과물은 "관절 점 몇 개"가 아니라 "정리된 자세 결과 꾸러미"로 보는 것이 좋다.

꾸러미 안에는 보통 아래가 들어 있다.

- 어떤 영상에서 나온 결과인지
- 몇 번째 프레임 결과인지
- 그 프레임의 시간 정보
- 관절 좌표 목록
- 분석에 쓸 수 있는 요약 구조

각 프레임 정보 안에는 보통 아래가 있다.

- `frameIndex`
- `timestampMs`
- `poseDetected`
- `landmarks`

### 아키텍처 연동 설명

설계 기준 데이터 구조는 아래가 중심이다.

- `PoseInferenceService.infer()` 반환 리스트
- `SkeletonMapperService.map_landmarks()` 반환 skeleton
- `MotionAnalysisResult.skeleton`

이 구조는 향후 실제 `PoseLandmarkerResult` 전체를 별도 schema로 감싸더라도 기준 문서 역할을 할 수 있다.

---

## 9. 이 기능이 다른 기능과 연결되는 방식

### 쉬운 설명

이 기계는 혼자 끝나는 완성품이 아니라, 다음 기계에 재료를 넘기는 중간 장치다.

연결 대상은 주로 아래 세 개다.

1. 스켈레톤 정리기
2. 운동 분석기
3. 피드백 생성기

즉, 포즈 랜드마커는 "영상 분석 공정에서 몸 좌표를 공급하는 핵심 센서"다.

### 아키텍처 연동 설명

연결 순서는 보통 아래처럼 본다.

- `video_reader`
  -> `pose_inference`
  -> `skeleton_mapper`
  -> `analysis_pipeline`
  -> `llm_feedback`

따라서 이 기능의 출력 형식은 후속 단계가 그대로 소비하기 쉬운 구조여야 한다.

특히 아래 두 가지를 분리해서 생각해야 한다.

- 순수 추론 결과
- 분석 문맥이 붙은 스켈레톤 결과

---

## 10. 현재 임시 동작과 나중 동작의 차이

### 쉬운 설명

현재는 실사용 연결 전이라 "데모 모드"에 가깝다.

지금:

- 내부 샘플 영상 `backSquat.mp4` 기반 프레임을 사용한다.
- 실제 MediaPipe 대신 목업 랜드마크 생성 방식이 일부 섞여 있다.
- 흐름 검증이 우선이다.
- MVP v1에서는 2D 스켈레톤 출력만 목표로 한다.

나중:

- 실제 MediaPipe Pose Landmarker가 모델 파일을 로드한다.
- 각 프레임에 대해 진짜 포즈 추론을 수행한다.
- 추론 결과가 실제 운동 분석과 피드백 생성으로 이어진다.
- 추후 필요 시 3D world landmark와 다중 영상 융합으로 확장할 수 있다.

즉, 지금은 "배관 시험용 장비", 나중에는 "실제 판독 엔진이 연결된 제품"이다.

### 아키텍처 연동 설명

현재 반영된 임시 정책:

- `adapter/mediapipe_adapter.py`는 스텁 상태다.
- `service/pose_inference.py`는 중앙 기준점 기반 목업 랜드마크를 만든다.
- `service/skeleton_mapper.py`가 후속 분석용 skeleton 구조를 만든다.

향후 실제 연결 시 변경 포인트:

- MediaPipe Tasks Vision 의존성 추가
- `MediaPipeAdapter` 실제 구현
- `PoseInferenceService`에서 실제 `PoseLandmarkerResult` 사용
- 필요 시 segmentation mask, world landmark 등 확장 필드 반영

---

## 11. 성능 관점에서 이 기능이 중요한 이유

### 쉬운 설명

이 기능은 전체 분석 속도를 많이 좌우한다.

왜냐하면:

- 프레임 수가 많으면 추론 호출도 많아진다.
- 모델이 무거우면 시간이 늘어난다.
- RGB 변환이나 결과 직렬화도 비용이 든다.
- GPU를 못 쓰고 CPU fallback으로 내려가면 처리 시간이 크게 늘어날 수 있다.

즉, 포즈 랜드마커는 단순한 계산기가 아니라 전체 분석 속도를 좌우하는 핵심 엔진이다.

여기서 특히 모델 선택의 영향이 크다.

- `Lite`는 가장 가볍다.
- `Full`은 가장 균형이 좋다.
- `Heavy`는 GPU에서는 쓸 만해도 CPU fallback 시 병목이 커질 수 있다.

### 아키텍처 연동 설명

성능에 직접 연결되는 주요 선택지는 아래와 같다.

- `running_mode`
- `num_poses`
- 입력 해상도
- 프레임 샘플링 밀도
- RGB 변환 시점
- GPU 사용 가능 여부와 fallback 발생 빈도
- 선택한 모델이 `Lite`, `Full`, `Heavy` 중 무엇인지
- 추후 후보:
  - `output_segmentation_masks`
  - `batch_profile`

이 내용은 `MediaPipe 기반 포즈 랜드마커 기능 아키텍처.md`와 같이 봐야 한다.

---

## 12. 이 기능이 실패하는 경우

### 쉬운 설명

이 기계는 아래 경우에 정상 작동하지 않을 수 있다.

- 모델 파일이 없다.
- 모델은 있어도 초기화에 실패한다.
- GPU 초기화에 실패해 CPU fallback까지 모두 실패한다.
- 프레임 형식이 맞지 않는다.
- 추론 중 내부 오류가 난다.
- 결과를 정리하는 과정에서 필요한 값이 비어 있다.

즉, 재료가 문제이거나, 판독기가 문제이거나, 정리 단계가 문제일 수 있다.

특히 `Heavy` 모델은 GPU 가속이 실패해 CPU fallback으로 내려가면 응답 시간이 크게 늘어날 수 있다.

### 아키텍처 연동 설명

대표 예외 후보:

- `ModelAssetNotFoundError`
- `LandmarkerInitializationError`
- `InvalidFrameInputError`
- `PoseInferenceError`
- `ResultSerializationError`

이 예외들은 추후 `adapter/mediapipe_adapter.py`와 `service/pose_inference.py`에 명확히 분리하는 것이 좋다.

---

## 13. 한 줄 요약

### 쉬운 설명

MediaPipe 기반 포즈 랜드마커 기능은 "영상 장면을 넣으면 사람 몸의 주요 관절 위치를 찾아서, 다음 분석 장치가 바로 쓸 수 있는 자세 데이터로 정리해 주는 장치"다.

### 아키텍처 연동 설명

시스템 관점에서 이 기능은 `프레임 입력 -> MediaPipe 포즈 추론 -> 스켈레톤 매핑 -> 분석 연결`의 핵심 처리 계층이며, `video_reader -> pose_inference -> mediapipe_adapter -> skeleton_mapper -> 후속 service` 흐름의 중심이다.
