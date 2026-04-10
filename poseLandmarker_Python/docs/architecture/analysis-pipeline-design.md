# 데이터분석 파이프라인 구현 설계

## 1. 문서 목적

이 문서는 `service/analysis_pipeline.py`를 실제 운동역학 분석 파이프라인으로 구현하기 위한 설계 기준이다.

다루는 내용:

- 각 분석 모듈의 책임과 인터페이스
- 모듈 간 데이터 흐름과 중간 포맷
- 구체적인 계산 항목과 알고리즘 기준
- 분석 결과 출력 스키마
- 구현 순서 기준

기존 `data-analysis-pipeline-guide.md`는 협업 구조 안내서이며, 이 문서는 그 위에서 **실제 무엇을 어떻게 계산할 것인가**를 정의한다.

### 분석 철학: 초개인화

이 파이프라인은 **사람 간 비교를 목표로 하지 않는다.**

분석 대상은 한 사람의 특정 동작이며, 그 사람의 신체 구조 자체가 분석의 기준선이 된다. 대퇴골이 긴 사람은 스쿼트 시 상체 전경이 더 클 수밖에 없다. 이것을 "표준 각도 초과"로 경고하는 것은 틀린 피드백이다.

따라서:

- 좌표 정규화(사람 간 스케일 통일)는 하지 않는다.
- 개인의 신체 비율(분절 길이, 좌우 비대칭 베이스라인)을 skeleton에서 직접 추출하여 분석 파라미터로 사용한다.
- 위험 판정과 KPI는 **그 사람의 신체 구조를 고려한 상대 기준**으로 계산한다.

---

## 2. 파이프라인 전체 흐름

```text
skeleton JSON (input)
  └─ [1] Preprocessing       → clean_frames
  └─ [2] Body Profile        → body_profile   ← 개인 신체 비율 추출
  └─ [3] Feature Extraction  → feature_set    ← 각도, 속도, 부하 비율
  └─ [3.5] CoP Analysis      → ground_ref, feature_set.cop_*  ← 지면 기준 + CoM/CoP/모멘트 암
  └─ [4] Rep Segmentation    → rep_segments
  └─ [5] KPI Calculation     → kpis           ← body_profile + CoP 기반 상대 지표
  └─ [6] Event Detection     → events
  └─ [7] Issue Detection     → issues         ← body_profile + CoP 기반 판정
  └─ [8] Result Assembly     → analysis (output)
```

각 단계는 독립 함수 또는 모듈로 분리한다.

`analysis_pipeline.py`의 `AnalysisPipelineService.analyze()`는 이 8단계를 순서대로 호출하는 **조립 책임만** 갖는다.

---

## 3. 입력 데이터 구조

분석 파이프라인이 받는 입력은 `skeleton_mapper.py`가 생성한 `skeleton` dict다.

### 3.1 현재 실제 skeleton 구조

```json
{
  "frames": [
    {
      "frameIndex": 0,
      "timestampMs": 0.0,
      "poseDetected": true,
      "landmarks": [
        {
          "name": "nose",
          "x": 0.355381,
          "y": 0.144323,
          "z": -0.419512,
          "visibility": 0.999905,
          "presence": 0.999856
        }
      ]
    }
  ],
  "videoInfo": {
    "videoSrc": "...",
    "displayName": "backSquat.mp4",
    "sourceFps": 30.0,
    "frameCount": 320,
    "width": 552,
    "height": 722,
    "backend": "FFMPEG",
    "extractedCount": 320,
    "requestedSamplingFps": 100.0,
    "effectiveSamplingFps": 30.0,
    "runningMode": "VIDEO",
    "modelName": "pose_landmarker_full.task",
    "detectedFrameCount": 320
  },
  "nextTimestampCursorMs": 10731.0
}
```

### 3.2 MediaPipe 33 landmark 이름 순서

```python
LANDMARK_NAMES = [
    "nose",              # 0
    "left_eye_inner",    # 1
    "left_eye",          # 2
    "left_eye_outer",    # 3
    "right_eye_inner",   # 4
    "right_eye",         # 5
    "right_eye_outer",   # 6
    "left_ear",          # 7
    "right_ear",         # 8
    "mouth_left",        # 9
    "mouth_right",       # 10
    "left_shoulder",     # 11
    "right_shoulder",    # 12
    "left_elbow",        # 13
    "right_elbow",       # 14
    "left_wrist",        # 15
    "right_wrist",       # 16
    "left_pinky",        # 17
    "right_pinky",       # 18
    "left_index",        # 19
    "right_index",       # 20
    "left_thumb",        # 21
    "right_thumb",       # 22
    "left_hip",          # 23
    "right_hip",         # 24
    "left_knee",         # 25
    "right_knee",        # 26
    "left_ankle",        # 27
    "right_ankle",       # 28
    "left_heel",         # 29
    "right_heel",        # 30
    "left_foot_index",   # 31
    "right_foot_index",  # 32
]
```

좌표 기준:

- `x`, `y`: 이미지 정규화 좌표 (0~1)
- `z`: 깊이 추정값 (hip을 0 기준으로 한 상대값, 단위 없음)
- `visibility`, `presence`: 각각 가시성과 존재 확률 (0~1)

---

## 4. 모듈 설계

### 4.1 `analysis_preprocess.py` — 전처리

**책임**: 분석 이전에 프레임 품질을 정리한다.

**입력**: `skeleton["frames"]`

**출력**: `List[FrameData]` (내부 구조체)

**처리 항목**:

1. `poseDetected=false` 프레임 제거 또는 마킹
2. `visibility < VISIBILITY_THRESHOLD` 관절 마킹 (기본값: `0.5`)
3. 보간 (linear interpolation): 연속 누락 구간이 짧으면 (`≤ MAX_GAP_FRAMES`, 기본값: `3`) 보간, 아니면 해당 구간 제외
4. 시간축 정렬 보장 (`timestampMs` 오름차순)

**내부 포맷 (`FrameData`)**:

```python
@dataclass
class JointData:
    name: str
    x: float
    y: float
    z: float
    visibility: float
    presence: float
    is_reliable: bool  # visibility >= threshold

@dataclass
class FrameData:
    frame_index: int
    timestamp_ms: float
    pose_detected: bool
    joints: dict[str, JointData]  # name → JointData
    is_usable: bool  # pose_detected and 핵심 관절 신뢰도 충족
```

**핵심 관절 기준** (squat 기준):

```python
SQUAT_REQUIRED_JOINTS = {
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_shoulder", "right_shoulder",
}
```

---

### 4.2 `analysis_body_profile.py` — 신체 비율 프로파일링

**책임**: skeleton에서 개인의 신체 분절 길이와 구조적 비율을 추출한다. 이 값은 이후 모든 판정 기준의 기준선이 된다.

**입력**: `List[FrameData]` (전처리 완료)

**출력**: `BodyProfile`

```python
@dataclass
class BodyProfile:
    # 분절 길이 (정규화 좌표 기준 상대 길이)
    left_femur_len: float        # left_hip → left_knee
    right_femur_len: float       # right_hip → right_knee
    left_tibia_len: float        # left_knee → left_ankle
    right_tibia_len: float       # right_knee → right_ankle
    torso_len: float             # hip_center → shoulder_center
    left_upper_arm_len: float    # left_shoulder → left_elbow
    right_upper_arm_len: float   # right_shoulder → right_elbow

    # 비율 지표 (판정 기준선 계산에 사용)
    femur_to_torso_ratio: float  # (left+right femur 평균) / torso
    tibia_to_femur_ratio: float  # tibia / femur 평균
    limb_asymmetry: dict[str, float]  # 좌우 길이 차이 비율
    joint_angle_baseline_deg: dict[str, float]  # standing 구간 기준 좌우 각도 차이 baseline

    # 계산에 사용한 프레임 수 (신뢰도 참고용)
    sample_frame_count: int
```

**계산 방법**:

분절 길이는 동작 중에도 실제 길이는 변하지 않으므로, **여러 프레임의 중앙값**을 취해 추정 안정성을 높인다.

```python
# 예시: left_femur_len
distances = [
    dist(frame.joints["left_hip"], frame.joints["left_knee"])
    for frame in frames if frame.is_usable
]
left_femur_len = median(distances)
```

**`femur_to_torso_ratio`의 역할**:

스쿼트에서 이 비율이 높을수록(대퇴골이 상대적으로 길수록) 구조적으로 더 큰 상체 전경이 불가피하다. 다만 MVP v1에서는 이 값만으로 "정답 자세 각도"를 단정하지 않는다. 대신:

- `reference_trunk_lean` 계산 시 체형 비율을 1차 priors로 사용한다.
- 실제 세션의 상단 구간(top position)과 반복별 최저점 분포를 함께 반영해 **개인 참조 범위(reference band)** 를 만든다.
- warning은 절대 각도 자체보다 이 개인 참조 범위를 얼마나 벗어났는지로 판정한다.

```text
reference_trunk_lean = f(femur_to_torso_ratio, tibia_to_femur_ratio, rep depth, session median)
```

**`limb_asymmetry`의 역할**:

좌우 분절 길이 차이가 일정 수준 이상이면(예: `> 3%`) 개인의 구조적 비대칭으로 기록한다. 이후 좌우 부하 불균형 판정 시 이 베이스라인을 차감하여 **움직임에서 비롯된 비대칭**과 **구조적 비대칭**을 구분한다.

---

### 4.3 `analysis_features.py` — 피처 추출

**책임**: 좌표 데이터를 분석 가능한 수치 피처로 변환한다.

**입력**: `List[FrameData]`

**출력**: `FeatureSet`

```python
@dataclass
class FeatureSet:
    timestamps_ms: List[float]
    joint_angles: dict[str, List[float]]      # 관절 이름 → 시계열 각도
    joint_velocities: dict[str, List[float]]  # 관절 이름 → 시계열 속도
    hip_heights: List[float]                  # hip_center y 좌표 시계열 (원본 좌표)
    bar_path_x: List[float]                   # 손목 중점 x 시계열
    load_ratios: dict[str, List[float]]       # 좌우 관절별 부하 분산 비율 시계열

    # CoP / CoM 시계열 (analysis_cop.py에서 채워짐)
    com_x: List[float]                        # 전신 CoM x 시계열
    com_y: List[float]                        # 전신 CoM y 시계열
    cop_ap_normalized: List[float | None]     # 측면뷰 전후 CoP 정규화 시계열
    cop_ml_normalized: List[float | None]     # 정면뷰 좌우 CoP 정규화 시계열
    moment_arms: dict[str, List[float]]       # 관절별 모멘트 암 시계열
                                              # keys: left_ankle, right_ankle,
                                              #        left_knee, right_knee,
                                              #        left_hip, right_hip
    bar_over_midfoot: List[float | None]      # 바벨 x - 발중심 x 시계열 (없으면 None)
```

**계산 항목**:

#### 관절 각도

삼각함수 기반 3점 각도 계산:

```python
def calc_angle(a: tuple, b: tuple, c: tuple) -> float:
    """b를 꼭짓점으로 하는 a-b-c 각도 (도 단위)"""
    ba = (a[0]-b[0], a[1]-b[1])
    bc = (c[0]-b[0], c[1]-b[1])
    cos_angle = dot(ba, bc) / (norm(ba) * norm(bc) + 1e-9)
    return degrees(arccos(clip(cos_angle, -1.0, 1.0)))
```

squat 기준 계산 항목:

| 이름 | 꼭짓점 | 세 관절 |
|------|--------|--------|
| `left_knee_angle` | left_knee | left_hip, left_knee, left_ankle |
| `right_knee_angle` | right_knee | right_hip, right_knee, right_ankle |
| `left_hip_angle` | left_hip | left_shoulder, left_hip, left_knee |
| `right_hip_angle` | right_hip | right_shoulder, right_hip, right_knee |
| `trunk_lean_angle` | shoulder_center | shoulder_center, hip_center, 수직축 가상점 |

#### 속도

```python
velocity[i] = (position[i+1] - position[i-1]) / (2 * dt)
```

여기서 `dt = (timestamps_ms[i+1] - timestamps_ms[i-1]) / 2000.0` (초 단위)

#### 좌우 부하 분산 비율

좌우 무릎 각도 차이에서 **standing 구간에서 관측한 개인 baseline 각도 차이**를 차감해 순수 움직임 비대칭을 계산한다. 길이 비율(`limb_asymmetry`)은 구조적 참고 정보로 남기되, 각도 시계열에서 직접 빼지 않는다.

```python
structural_baseline_deg = body_profile.joint_angle_baseline_deg.get("knee", 0.0)
movement_asymmetry = abs(left_knee_angle - right_knee_angle) - structural_baseline_deg
load_ratio_knee = max(0.0, movement_asymmetry) / 180.0
# 0.0 = 구조적 차이 범위 내, 높을수록 움직임에서 비롯된 불균형
```

---

### 4.4 `analysis_reps.py` — Rep 구간 분할

**책임**: 운동의 반복 구간(rep)을 분할한다.

**입력**: `FeatureSet`

**출력**: `List[RepSegment]`

```python
@dataclass
class RepSegment:
    rep_index: int         # 1-based
    start_ms: float
    end_ms: float
    bottom_ms: float       # 최저점 타임스탬프 (squat: 최대 굴곡 시점)
    phase_eccentric_ms: float   # 내려가기 구간 시작
    phase_concentric_ms: float  # 올라오기 구간 시작
    depth_angle_deg: float      # 최저점 무릎 각도
```

**Rep 탐지 알고리즘 (squat)**:

hip_center y 좌표(원본 정규화 이미지 좌표)는 squat의 내려가기에서 증가(아래 방향), 올라오기에서 감소한다.

1. `hip_height` 시계열에 Savitzky-Golay 필터를 적용하여 노이즈 제거
2. 국소 최댓값(peak)을 squat 최저점으로 탐지 (`scipy.signal.find_peaks` 또는 직접 구현)
3. 인접 국소 최솟값(valley)을 기준으로 rep 시작/종료 경계 확정
4. 최저점 구간이 너무 짧으면 (< `MIN_REP_DURATION_MS`, 기본값: `500ms`) 노이즈로 간주하고 제외

---

### 4.5 `analysis_kpis.py` — KPI 계산

**책임**: rep 구간을 기반으로 개인 특성을 반영한 성과 지표를 산출한다.

**입력**: `FeatureSet`, `List[RepSegment]`, `BodyProfile`

**출력**: `List[KPI]`

```python
@dataclass
class KPI:
    key: str
    label: str
    value: float
    unit: str
    description: str
    personal_context: str | None  # 개인 신체 특성을 고려한 해석 메모
```

**squat 기준 KPI 목록**:

| key | label | 계산 방법 | unit |
|-----|-------|-----------|------|
| `rep_count` | 반복 횟수 | len(rep_segments) | reps |
| `avg_depth_angle` | 평균 최저 무릎 각도 | mean(depth_angle_deg) per rep | deg |
| `depth_consistency` | rep 간 깊이 일관성 | 1 - (std(depth_angle_deg) / mean(depth_angle_deg)) | ratio |
| `avg_rep_duration_ms` | 평균 rep 소요 시간 | mean(end_ms - start_ms) per rep | ms |
| `tempo_consistency` | rep 간 템포 일관성 | 1 - (std(duration) / mean(duration)) | ratio |
| `avg_eccentric_ratio` | 내려가기 비율 | mean((bottom_ms - start_ms) / (end_ms - start_ms)) | ratio |
| `avg_trunk_lean` | 평균 상체 기울기 | mean(trunk_lean_angle) | deg |
| `expected_trunk_lean` | 개인 참조 상체 기울기 | body_profile + 세션 분포 기반 참조값 | deg |
| `trunk_lean_excess` | 개인 참조 대비 상체 전경 초과분 | avg_trunk_lean - expected_trunk_lean | deg |
| `avg_load_ratio_knee` | 평균 무릎 부하 불균형 | mean(load_ratio_knee), 구조적 비대칭 차감 후 | ratio |
| `cop_bottom_ap` | 최저점 전후 CoP 위치 | rep 최저점 시점의 `cop_ap_normalized` 평균, 측면뷰 한정 | ratio |
| `cop_bottom_ml` | 최저점 좌우 CoP 위치 | rep 최저점 시점의 `cop_ml_normalized` 평균, 정면뷰 한정 | ratio |
| `cop_ap_consistency` | rep 간 전후 CoP 일관성 | 1 - std(cop_bottom_ap) / personal_thresholds.cop_ap_range | ratio |
| `cop_ml_consistency` | rep 간 좌우 CoP 일관성 | 1 - std(cop_bottom_ml) / personal_thresholds.cop_ml_range | ratio |
| `cop_anterior_shift` | 하강 중 CoP 전방 이동량 | max(cop_ap_normalized) - cop_ap_normalized at start, 측면뷰 한정 | ratio |
| `avg_knee_moment_arm` | 평균 무릎 모멘트 암 | mean(left_knee_moment_arm + right_knee_moment_arm) / 2 at bottom | normalized |
| `avg_hip_moment_arm` | 평균 고관절 모멘트 암 | mean(left_hip + right_hip moment arm) at bottom | normalized |
| `knee_hip_moment_ratio` | 무릎/고관절 부하 비율 | avg_knee_moment_arm / avg_hip_moment_arm at bottom | ratio |
| `bar_midfoot_offset` | 바벨-발중심 괴리 | mean(bar_over_midfoot) across rep | normalized |

`expected_trunk_lean`과 `trunk_lean_excess`는 "정답 자세"가 아니라 개인 참조선이다. 대퇴골이 긴 사람에게 `avg_trunk_lean`이 40°이면 정상일 수 있고, 짧은 사람에게는 과도할 수 있다. 또 같은 사람이라도 촬영 각도와 반복 깊이에 따라 참조선이 달라질 수 있으므로 세션 분포를 함께 반영한다.

**CoP KPI 해석 기준**:

`knee_hip_moment_ratio`는 스쿼트의 관절 부하 분배 패턴을 단일 숫자로 요약한다:

- 값 > 1.0: 무릎 우세 패턴 (CoP 전방, 무릎 모멘트 암 > 고관절 모멘트 암) → 대퇴사두 및 슬개건 부하 증가
- 값 < 1.0: 고관절 우세 패턴 (CoP 후방, 고관절 모멘트 암 > 무릎 모멘트 암) → 둔근/척추기립근 부하 증가
- 개인의 해부학적 구조(`femur_to_torso_ratio`)에 따라 어느 쪽이 "자연스러운" 패턴인지 달라진다

`cop_anterior_shift`는 하강 중 CoP가 얼마나 앞으로 이동하는지를 나타낸다. 높을수록 대퇴사두 과부하 위험이 있으며, 측면 촬영에서만 신뢰할 수 있다.

`bar_midfoot_offset`은 Rippetoe 발 중심 원칙과의 괴리를 정량화한다. 양수(앞)이면 바벨이 발 중심보다 앞에 있어 지레 효과로 척추 부하가 증가한다.

---

### 4.6 `analysis_events.py` — 이벤트 탐지

**책임**: 시간 정보가 있는 특정 시점을 이벤트로 기록한다.

**입력**: `FeatureSet`, `List[RepSegment]`

**출력**: `List[Event]`

```python
@dataclass
class Event:
    type: str
    timestamp_ms: float
    rep_index: int | None
    metadata: dict
```

**기본 이벤트 타입**:

| type | 설명 |
|------|------|
| `rep_start` | rep 시작 시점 |
| `rep_bottom` | squat 최저점 |
| `rep_end` | rep 종료 시점 |
| `pose_lost` | `poseDetected=false` 연속 구간 시작 |
| `pose_recovered` | 포즈 복구 시점 |

---

### 4.7 `analysis_cop.py` — 지면 벡터 및 수직저항무게중심(CoP) 분석

**책임**: skeleton 좌표에서 지면 기준선과 전신 무게중심(CoM)을 추정하고, 준정적 근사(quasi-static approximation) 하에서 수직저항무게중심(Center of Pressure, CoP)을 산출한다. 각 관절의 모멘트 암(moment arm)을 계산해 관절 부하 패턴을 정량화한다.

**이론 배경: 왜 CoP가 중요한가**

중량 스쿼트에서 지면 반력(Ground Reaction Force)은 발바닥의 CoP를 통해 작용한다. 준정적 조건(느린 동작, 가속도 ≈ 0)에서:

```text
CoP ≈ 전신 CoM의 수평 투영점
```

CoP 위치는 모든 관절의 모멘트 암을 결정한다:

```text
관절 토크 ∝ 모멘트 암 × 수직하중(체중 + 바벨 하중)

발목 모멘트 암 = |CoP_x - ankle_x|
무릎 모멘트 암 = |CoP_x - knee_x|   (CoM 수직선 기준)
엉덩이 모멘트 암 = |CoP_x - hip_x|  (CoM 수직선 기준)
```

CoP가 발 중심에서 앞쪽(anterior)으로 이동할수록 → 무릎/대퇴사두 부하 증가  
CoP가 뒤쪽(posterior)으로 이동할수록 → 고관절/둔근/척추기립근 부하 증가  
CoP가 좌우 비대칭이면 → 한쪽 관절 과부하, 척추 측만 스트레스

**입력**: `List[FrameData]`, `BodyProfile`

**출력**: `GroundRef`, `List[CoPFrame]`, `List[BarPositionEstimate]`

#### 지면 기준선 추출 (`GroundRef`)

```python
@dataclass
class GroundRef:
    ground_y: float          # 지면 Y 좌표 (정규화 이미지 좌표, 0~1)
                             # = median(max(left_heel.y, right_heel.y)) on standing frames only
    mid_foot_x: float        # 양발 중심 X 좌표 (CoP 기준점)
                             # = mean(left_heel.x, left_foot_index.x,
                             #        right_heel.x, right_foot_index.x)
    left_foot_vec: tuple[float, float]   # (foot_index.x - heel.x, foot_index.y - heel.y) normalized
    right_foot_vec: tuple[float, float]  # 우측 동일
    foot_width: float        # 좌우 발 중심 간 거리 (정면뷰 ML 정규화 기준)
    sagittal_foot_length: float | None   # 측면뷰에서 사용한 발 길이 proxy
    sample_frame_count: int
    view_type: str           # "sagittal" | "frontal" | "unknown"
    view_confidence: float   # 0.0~1.0
```

`ground_y`는 시작/끝 standing 구간만 사용해 계산한다. MVP v1에서는 전체 프레임에서 자동 선별하지 않고, 분석 시작부와 종료부에서 hip_center y 변화량이 작고 양발 heel/foot landmark가 안정적인 프레임만 모아 heel y 중앙값으로 지면 기준선을 만든다.

#### 전신 무게중심(CoM) 추정

Winter (2009) 인체 분절 모델을 기반으로 7분절 근사를 사용한다:

```python
# (근위 랜드마크, 원위 랜드마크, CoM 위치 비율, 체중 대비 질량 비율)
SEGMENTS = [
    ("mid_ear",          "nose",             0.58, 0.081),  # 두부
    ("hip_center",       "shoulder_center",  0.44, 0.424),  # 체간 (상/중/하 통합)
    ("left_shoulder",    "left_wrist",       0.50, 0.050),  # 좌 상지
    ("right_shoulder",   "right_wrist",      0.50, 0.050),  # 우 상지
    ("left_hip",         "left_knee",        0.433, 0.100), # 좌 대퇴
    ("right_hip",        "right_knee",       0.433, 0.100), # 우 대퇴
    ("left_knee",        "left_ankle",       0.433, 0.0465),# 좌 하퇴
    ("right_knee",       "right_ankle",      0.433, 0.0465),# 우 하퇴
    ("left_ankle",       "left_foot_index",  0.50, 0.0145), # 좌 발
    ("right_ankle",      "right_foot_index", 0.50, 0.0145), # 우 발
]
# 질량 비율 합계: ~1.0 (정규화 후 사용)
```

```python
def estimate_com(joints: dict[str, JointData], segments=SEGMENTS) -> tuple[float, float]:
    total_x = total_y = total_mass = 0.0
    for (prox, dist, com_frac, mass_frac) in segments:
        p = joints.get(prox)
        d = joints.get(dist)
        if p is None or d is None:
            continue
        seg_x = p.x + com_frac * (d.x - p.x)
        seg_y = p.y + com_frac * (d.y - p.y)
        total_x += seg_x * mass_frac
        total_y += seg_y * mass_frac
        total_mass += mass_frac
    return (total_x / total_mass, total_y / total_mass)
```

`mid_ear`는 `left_ear`와 `right_ear`의 중점으로 계산한다.

#### 바 위치 추정 (`BarPositionEstimate`)

백스쿼트에서 양 손목은 바벨을 잡고 있다. 따라서:

```text
bar_x ≈ (left_wrist.x + right_wrist.x) / 2
bar_y ≈ (left_wrist.y + right_wrist.y) / 2
```

이 근사는 바가 손목을 통과하므로 수평 위치(`x`)에서는 충분히 정확하다. 수직 위치(`y`)는 그립 방식(엄지 방향, 손목 꺾임)에 따라 수 cm 오차가 있을 수 있으나 CoP 분석에서는 `x`가 핵심이다.

```python
@dataclass
class BarPositionEstimate:
    x: float              # (left_wrist.x + right_wrist.x) / 2
    y: float              # (left_wrist.y + right_wrist.y) / 2
    confidence: float     # 0.0~1.0, 아래 기준으로 계산
    source: str           # "wrist_midpoint" | "manual" | "unavailable"

    # 진단용 필드
    wrist_spread: float   # |left_wrist.x - right_wrist.x|
                          # 너무 좁으면 클로즈그립, 너무 넓으면 와이드그립
    wrist_height_ratio: float  # (ground_y - bar_y) / (ground_y - shoulder_y)
                               # 1.0 = 어깨 높이, 0.0 = 지면 — 스쿼트에서는 0.7~1.1 예상
```

**신뢰도(`confidence`) 계산 기준**:

| 조건 | 차감 |
|------|------|
| left_wrist 또는 right_wrist의 `visibility < 0.5` | -0.5 |
| `wrist_height_ratio < 0.5` (바가 지나치게 낮음 → 데드리프트 가능성) | -0.3 |
| `wrist_height_ratio > 1.3` (바가 어깨 위 → 오버헤드 가능성) | -0.3 |
| `wrist_spread < 0.05` (손목 간격 너무 좁음 → 포즈 오류 가능) | -0.2 |

`confidence < 0.5`이면 해당 프레임의 bar position을 CoP 계산에 포함하지 않고, `bar_position_unavailable`로 마킹한다.

**바 위치로 CoP 보강 (바 하중 알 경우)**:

사용자가 총 하중(`total_load_kg`)을 입력하면 바벨의 무게를 계통에 포함할 수 있다:

```python
def augmented_cop_x(
    com_x: float,
    bar_x: float,
    body_mass_kg: float,   # 사용자 입력 (없으면 추정 불가)
    bar_load_kg: float,    # 사용자 입력 (바벨 포함 총 하중 - 체중)
) -> float:
    total = body_mass_kg + bar_load_kg
    return (body_mass_kg * com_x + bar_load_kg * bar_x) / total
```

바 하중을 모를 경우에는 `augmented_cop_x`를 계산하지 않고, 대신 `bar_x`와 `com_x`의 **괴리(offset)**를 별도 시계열로 기록해 패턴 분석에 활용한다:

```python
bar_com_offset = bar_x - com_x
# 양수: 바가 CoM 앞에 있음 (척추 굴곡 토크 증가)
# 음수: 바가 CoM 뒤에 있음 (드물지만 극단적 고관절 패턴)
```

구현 확장 포인트:

- `bar_confidence`를 프레임별로 저장해 손목 visibility 저하 구간을 제외할 수 있어야 한다.
- 사용자 입력에 `body_mass_kg`, `bar_load_kg`가 있으면 `augmented_cop_x`를 함께 계산한다.
- 하중 정보가 없으면 `cop_x = com_x`를 유지하고, `bar_com_offset`과 `bar_over_midfoot_offset`만으로 상대 패턴을 해석한다.

**Rippetoe mid-foot 원칙**: 효율적 스쿼트에서 바는 발 중심 바로 위에 있어야 한다. 이 원칙을 바 하중 여부와 무관하게 검증할 수 있다:

```python
bar_over_midfoot_offset = bar_x - ground_ref.mid_foot_x
# 0에 가까울수록 이상적, |값| > 0.05이면 비효율 경고
```

#### CoP 프레임 데이터

```python
@dataclass
class CoPFrame:
    frame_index: int
    timestamp_ms: float
    com_x: float            # 전신 CoM X (이미지 정규화 좌표)
    com_y: float            # 전신 CoM Y
    cop_x: float            # 추정 CoP X ≈ com_x (준정적 근사)
    cop_ap_normalized: float | None  # 측면뷰: (cop_x - mid_foot_x) / sagittal_foot_length
    cop_ml_normalized: float | None  # 정면뷰: (cop_x - mid_foot_x) / foot_width

    # 관절별 모멘트 암 (CoP에서 각 관절 중심까지의 수평 거리)
    left_ankle_moment_arm: float     # |cop_x - left_ankle.x|
    right_ankle_moment_arm: float
    left_knee_moment_arm: float      # |com_x - left_knee.x|
    right_knee_moment_arm: float
    left_hip_moment_arm: float       # |com_x - left_hip.x|
    right_hip_moment_arm: float

    # 바벨 추정 위치 (중량 스쿼트 시 참고)
    bar_x: float | None
    bar_over_midfoot_offset: float | None  # bar_x - mid_foot_x (양수 = 앞, 음수 = 뒤)
```

#### 준정적 근사의 유효 범위

이 근사는 다음 조건에서 유효하다:

- 동작 속도가 느릴수록 정확 (3RM 이상의 중량 스쿼트에서 특히 적합)
- 최저점 전후 가속도 전환 구간에서는 오차 발생 가능
- 동적 효과를 반영하려면 관성항이 필요하나, skeleton 데이터만으로는 신체 질량을 알 수 없으므로 현 단계에서는 준정적 근사로 제한

카메라 뷰 방향에 따른 제약:
- **측면 촬영(sagittal view)**: `x` 축이 전후 방향 → CoP 전후 분석에 가장 정확
- **정면 촬영(frontal view)**: `x` 축이 좌우 방향 → 측방 CoP 비대칭 분석에 유용, 전후 분석은 `z`(depth) 추정에 의존하므로 신뢰도 낮음

MVP v1에서는 유튜브 등 다양한 source의 원본 영상을 세션마다 다르게 받을 수 있고, 촬영 위치 메타데이터를 신뢰할 수 없다. 따라서 뷰 방향은 **자동 탐지**로 통일한다.

```python
@dataclass
class ViewInference:
    view_type: Literal["sagittal", "frontal", "unknown"]
    confidence: float
    signals: dict[str, float]  # shoulder/hip width ratio, 좌우 관절 depth 분산, foot orientation 등
```

자동 탐지 원칙:

1. `detect_view(clean_frames)`가 `ViewInference`를 먼저 산출한다.
2. `confidence >= 0.7`일 때만 해당 view 전용 CoP KPI를 활성화한다.
3. `confidence < 0.7` 또는 `view_type == "unknown"`이면 CoP 방향성 KPI와 관련 warning은 생성하지 않고 `cop_analysis_unavailable`만 남긴다.
4. 동일 세션에서 view가 흔들리면(frame별 판정 불안정) 전체 결과는 `unknown`으로 강등한다.

---

### 4.8 `analysis_issues.py` — 이상 탐지

**책임**: 개인 신체 특성을 기준선으로 삼아 움직임 문제와 데이터 품질 문제를 탐지한다. `error`는 고정 품질 기준을 허용하지만, `warning`은 개인 기준선에서 파생한 상대 임계값으로 판정한다.

**입력**: `FeatureSet`, `List[RepSegment]`, `List[KPI]`, `BodyProfile`

**출력**: `List[Issue]`

```python
@dataclass
class Issue:
    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    timestamp_ms: float | None   # 특정 시점 문제이면 기록
    rep_index: int | None
    context: dict                # 판정에 사용된 수치 포함
```

**판정 원칙**:

- `error`: 데이터 품질 문제 또는 분석 불가 조건. 고정 기준 허용.
- `warning`: 움직임 문제. 반드시 `BodyProfile` + 세션 baseline + `ViewInference` 기반 상대 기준으로 판정.
- `info`: 패턴 참고 정보. 경고 수준은 아니지만 LLM 피드백 입력으로 유용한 것.

```python
personal_thresholds = build_personal_thresholds(
    body_profile=body_profile,
    rep_segments=rep_segments,
    kpis=kpis,
    view_type=ground_ref.view_type,
    view_confidence=ground_ref.view_confidence,
)
```

**squat 기준 탐지 항목**:

| code | severity | 판정 기준 |
|------|----------|----------|
| `no_reps_detected` | error | rep_count == 0 |
| `low_detection_ratio` | error | detection_ratio < 0.8 |
| `excessive_trunk_lean` | warning | `trunk_lean_excess > personal_thresholds.trunk_lean_excess_deg` |
| `movement_load_imbalance` | warning | `avg_load_ratio_knee > personal_thresholds.load_imbalance_warn` |
| `insufficient_depth` | warning | `avg_depth_angle > personal_thresholds.depth_angle_upper_deg` |
| `depth_inconsistency` | warning | `depth_consistency < personal_thresholds.depth_consistency_min` |
| `tempo_inconsistency` | info | tempo_consistency < 0.75 |
| `short_rep_duration` | info | rep 중 하나라도 duration < 1000ms |
| `structural_asymmetry_noted` | info | limb_asymmetry 중 하나라도 > 3% — 경고가 아닌 개인 특성 기록 |
| `cop_anterior_overload` | warning | `view_type == "sagittal"` 이고 `cop_bottom_ap > personal_thresholds.cop_ap_forward_warn` |
| `cop_posterior_instability` | warning | `view_type == "sagittal"` 이고 `cop_bottom_ap < personal_thresholds.cop_ap_backward_warn` |
| `cop_lateral_asymmetry` | warning | `view_type == "frontal"` 이고 `abs(cop_bottom_ml) > personal_thresholds.cop_ml_asymmetry_warn` |
| `cop_instability` | warning | view별 consistency KPI가 `personal_thresholds` 미만 |
| `knee_dominant_loading` | info | knee_hip_moment_ratio > 1.5 at bottom: 무릎 우세 부하 패턴 (대퇴사두 과부하 경향) |
| `hip_dominant_loading` | info | knee_hip_moment_ratio < 0.5 at bottom: 고관절 우세 부하 패턴 (굿모닝 스쿼트 경향) |
| `bar_forward_of_midfoot` | warning | `bar_midfoot_offset > personal_thresholds.bar_midfoot_offset_warn` |
| `cop_analysis_unavailable` | info | view 자동 탐지 실패, 신뢰도 미달, 또는 필요한 CoP 시계열이 비어 있음 |

`structural_asymmetry_noted`는 warning이 아니다. 구조적 비대칭은 문제가 아니라 개인 특성이며, LLM 피드백이 이를 참고해 해석할 수 있도록 기록하는 것이다.

---

## 5. 분석 출력 스키마

`AnalysisPipelineService.analyze()`의 최종 반환 형식이다.

### 5.1 전체 구조

```json
{
  "summary": { ... },
  "bodyProfile": { ... },
  "groundRef": { ... },
  "kpis": [ ... ],
  "timeseries": { ... },
  "repSegments": [ ... ],
  "events": [ ... ],
  "issues": [ ... ]
}
```

### 5.2 `summary`

```json
{
  "exerciseType": "squat",
  "repCount": 5,
  "frameCount": 320,
  "durationMs": 10667.0,
  "sourceFps": 30.0,
  "sampledFps": 30.0,
  "detectionRatio": 1.0,
  "usableFrameCount": 320,
  "bodyweightKg": 125.0,
  "externalLoadKg": 260.0,
  "barPlacementMode": "auto",
  "barPlacementResolved": "low_bar",
  "totalSystemMassKg": 385.0
}
```

`detectionRatio`는 운동 수행 KPI가 아니라 데이터 품질 메타데이터다. 따라서 `summary`와 `issues`에서만 사용하고 `kpis` 목록에는 포함하지 않는다.

### 5.3 `groundRef`

```json
{
  "groundY": 0.918,
  "midFootX": 0.502,
  "footWidth": 0.183,
  "sagittalFootLength": null,
  "leftFootVec": [0.062, 0.008],
  "rightFootVec": [-0.058, 0.007],
  "sampleFrameCount": 42,
  "viewType": "sagittal",
  "viewConfidence": 0.91,
  "barPlacementInput": "auto",
  "barPlacementResolved": "low_bar",
  "bodyweightKg": 125.0,
  "externalLoadKg": 260.0,
  "totalSystemMassKg": 385.0
}
```

`viewType`은 자동 탐지 결과이며 `"sagittal"` / `"frontal"` / `"unknown"` 중 하나다. CoP 전후 분석은 `viewType == "sagittal"` 이고 `viewConfidence`가 충분할 때만 신뢰 가능하다.

### 5.5 `bodyProfile`

```json
{
  "leftFemurLen": 0.312,
  "rightFemurLen": 0.318,
  "leftTibiaLen": 0.274,
  "rightTibiaLen": 0.271,
  "torsoLen": 0.401,
  "leftUpperArmLen": 0.181,
  "rightUpperArmLen": 0.178,
  "femurToTorsoRatio": 0.787,
  "tibiaToFemurRatio": 0.877,
  "limbAsymmetry": {
    "femur": 0.019,
    "tibia": 0.011,
    "upperArm": 0.017
  },
  "jointAngleBaselineDeg": {
    "knee": 1.8,
    "hip": 2.4
  },
  "sampleFrameCount": 310
}
```

`bodyProfile`은 구조적 baseline만 담는다. `expected_trunk_lean`은 `bodyProfile`과 세션 분포를 함께 사용해 KPI 단계에서 계산한다.

### 5.6 `kpis`

```json
[
  {
    "key": "rep_count",
    "label": "반복 횟수",
    "value": 5,
    "unit": "reps",
    "description": "감지된 squat 반복 횟수",
    "personalContext": null
  },
  {
    "key": "avg_depth_angle",
    "label": "평균 최저 무릎 각도",
    "value": 87.3,
    "unit": "deg",
    "description": "최저점에서의 무릎 굴곡각 평균. 낮을수록 깊은 스쿼트",
    "personalContext": null
  },
  {
    "key": "trunk_lean_excess",
    "label": "체형 대비 상체 전경 초과",
    "value": 6.2,
    "unit": "deg",
    "description": "대퇴/상체 비율로 예상되는 기울기 대비 실제 초과분",
    "personalContext": "femurToTorsoRatio=0.787 기준 예상 기울기 32.5°"
  }
]
```

### 5.7 `timeseries`

차트용 시계열 데이터다.

```json
{
  "timestamps_ms": [0, 33, 66],
  "bar_placement_input": "auto",
  "bar_placement_resolved": "low_bar",
  "hip_height": [0.52, 0.518, 0.515],
  "bar_x": [0.505, 0.507, 0.511],
  "bar_y": [0.318, 0.321, 0.326],
  "bar_confidence": [0.92, 0.93, 0.91],
  "bar_com_offset": [0.007, 0.006, 0.007],
  "body_com_x": [0.498, 0.501, 0.504],
  "body_com_y": [0.481, 0.492, 0.507],
  "com_x": [0.503, 0.505, 0.508],
  "com_y": [0.372, 0.379, 0.386],
  "cop_ap_normalized": [0.02, 0.05, 0.09],
  "cop_ml_normalized": [null, null, null],
  "bar_over_midfoot": [0.003, 0.005, 0.007],
  "left_knee_angle": [172.3, 170.1, 168.4],
  "right_knee_angle": [171.8, 169.5, 167.9],
  "left_hip_angle": [168.0, 166.2, 164.5],
  "right_hip_angle": [167.5, 165.9, 164.1],
  "trunk_lean_angle": [5.2, 5.8, 6.3],
  "load_ratio_knee": [0.02, 0.03, 0.02],
  "moment_arm_left_knee": [0.031, 0.038, 0.045],
  "moment_arm_right_knee": [0.029, 0.036, 0.043],
  "moment_arm_left_hip": [0.041, 0.052, 0.061],
  "moment_arm_right_hip": [0.039, 0.050, 0.059],
  "moment_arm_left_ankle": [0.021, 0.028, 0.034],
  "moment_arm_right_ankle": [0.020, 0.027, 0.033]
}
```

현재 구현은 `augmented_cop_ap_normalized`를 별도 시계열로 내보내지 않는다. 대신 `body_com_x/body_com_y`, 질량가중합 이후 `com_x/com_y`, `bar_com_offset`, `bar_over_midfoot`를 함께 노출해 body CoM 대비 system CoM 이동을 해석한다.

### 5.8 `repSegments`

```json
[
  {
    "repIndex": 1,
    "startMs": 300.0,
    "endMs": 2100.0,
    "bottomMs": 1200.0,
    "phaseEccentricMs": 300.0,
    "phaseConcentricMs": 1200.0,
    "depthAngleDeg": 85.2
  }
]
```

### 5.9 `events`

```json
[
  { "type": "rep_start", "timestampMs": 300.0, "repIndex": 1, "metadata": {} },
  { "type": "rep_bottom", "timestampMs": 1200.0, "repIndex": 1, "metadata": { "knee_angle": 85.2 } },
  { "type": "rep_end", "timestampMs": 2100.0, "repIndex": 1, "metadata": {} }
]
```

### 5.10 `issues`

```json
[
  {
    "severity": "warning",
    "code": "movement_load_imbalance",
    "message": "구조적 비대칭을 제외한 무릎 부하 불균형이 감지됩니다.",
    "timestampMs": null,
    "repIndex": null,
    "context": {
      "avg_load_ratio_knee": 0.13,
      "structural_asymmetry_baseline": 0.019
    }
  },
  {
    "severity": "info",
    "code": "structural_asymmetry_noted",
    "message": "대퇴골 좌우 길이 차이가 감지됩니다. 이는 개인 신체 특성으로 경고가 아닙니다.",
    "timestampMs": null,
    "repIndex": null,
    "context": { "femur_asymmetry": 0.019 }
  }
]
```

### 5.11 `visualization`

프론트엔드 overlay와 차트가 같은 좌표계를 사용하도록, 분석 결과에 시각화 보조 블록을 추가할 수 있다. 선택 사항이지만 CoP, bar path, mid-foot 기준선을 디버깅할 때 유용하다.

```json
{
  "viewType": "sagittal",
  "viewConfidence": 0.91,
  "frameOverlays": [
    {
      "frameIndex": 120,
      "timestampMs": 4000.0,
      "points": {
        "midFoot": [0.502, 0.918],
        "com": [0.504, 0.507],
        "cop": [0.504, 0.918],
        "bar": [0.511, 0.326]
      },
      "lines": [
        { "type": "vertical", "x": 0.502, "label": "midfoot" },
        { "type": "vertical", "x": 0.504, "label": "cop" },
        { "type": "vertical", "x": 0.511, "label": "bar" }
      ]
    }
  ],
  "chartHints": {
    "copBands": [-0.3, 0.3],
    "barMidfootTolerance": 0.05
  }
}
```

권장 시각화 레이어:

- skeleton 위에 `midFoot`, `CoM`, `CoP`, `bar`를 점으로 표시
- `midFoot`, `CoP`, `bar`는 수직선으로 함께 표시해 정렬 여부를 즉시 확인
- 하단 차트에는 `cop_ap_normalized` 또는 `cop_ml_normalized`, `bar_com_offset`, `bar_over_midfoot`, `knee_hip_moment_ratio`를 rep 구간과 함께 렌더링
- `bar_confidence < 0.5` 프레임은 점선을 쓰거나 회색 처리해 추정 신뢰도 저하를 드러냄

---

## 6. 최종 `analysis_pipeline.py` 조립 구조

```python
class AnalysisPipelineService:
    def analyze(self, skeleton: dict, exercise_type: str | None = None) -> dict:
        frames_raw = skeleton.get("frames", [])
        video_info = skeleton.get("videoInfo", {})

        # [1] Preprocessing
        clean_frames = preprocess(frames_raw)

        # [2] Body Profile — 개인 신체 비율 추출
        body_profile = extract_body_profile(clean_frames)

        # [2.5] View Inference — 촬영 방향 자동 판정
        view_inference = detect_view(clean_frames)

        # [3] Feature Extraction
        features = extract_features(clean_frames, body_profile)

        # [3.5] CoP Analysis — 지면 기준 + CoM/CoP/모멘트 암 시계열
        ground_ref, features = extract_cop(clean_frames, features, body_profile,
                                           view_inference=view_inference)

        # [4] Rep Segmentation
        rep_segments = detect_reps(features, exercise_type=exercise_type)

        # [5] KPI Calculation — body_profile 기반 상대 지표
        kpis = calc_kpis(features, rep_segments, body_profile)

        # [6] Event Detection
        events = detect_events(features, rep_segments)

        # [7] Issue Detection — body_profile 기반 판정
        issues = detect_issues(features, rep_segments, kpis, body_profile)

        # [8] Assembly
        return assemble_result(
            exercise_type=exercise_type,
            video_info=video_info,
            body_profile=body_profile,
            ground_ref=ground_ref,
            features=features,
            rep_segments=rep_segments,
            kpis=kpis,
            events=events,
            issues=issues,
        )
```

각 호출 함수는 해당 모듈에서 import한다.

---

## 7. 신규 파일 목록

기존 `analysis_pipeline.py`를 조립 전용으로 유지하고, 아래 파일을 신규 생성한다.

```text
service/
  analysis_pipeline.py       # 조립 (기존 파일, 내용 교체)
  analysis_preprocess.py     # 전처리 + 내부 포맷 정의 (FrameData, JointData)
  analysis_body_profile.py   # 신체 비율 프로파일링 (BodyProfile)
  analysis_features.py       # 피처 추출 (각도, 속도, 부하 비율)
  analysis_cop.py            # 지면 벡터, CoM/CoP 추정, 모멘트 암 (GroundRef, CoPFrame)
  analysis_reps.py           # Rep 구간 분할
  analysis_kpis.py           # KPI 집계 (체형 + CoP 기반 상대 지표)
  analysis_events.py         # 이벤트 탐지
  analysis_issues.py         # 이상 탐지 (체형 + CoP 기반 판정)
```

---

## 8. 의존성 추가 후보

현재 `pyproject.toml` 기준으로 아래 패키지가 추가로 필요할 수 있다.

| 패키지 | 용도 | 필수 여부 |
|--------|------|----------|
| `scipy` | Savitzky-Golay 필터, peak detection | 권장 |
| `numpy` | 각도 계산, 벡터 연산 | 이미 포함 |

`scipy`가 부담스럽다면 rep 탐지와 smoothing을 직접 구현할 수 있다. 초기에는 단순 이동평균과 min-max 탐지로 대체 가능하다.

---

## 9. 구현 순서

### Phase 1. 내부 포맷 고정 (`analysis_preprocess.py`)

- `FrameData`, `JointData` 정의
- `preprocess()` 구현
- 샘플 skeleton 입력으로 단독 실행 확인

완료 기준: `preprocess(skeleton["frames"])`가 `List[FrameData]`를 반환한다.

### Phase 2. 신체 비율 프로파일링 (`analysis_body_profile.py`)

- `BodyProfile` 정의
- `extract_body_profile()` 구현 (분절 중앙값, 비율 계산, standing baseline 각도 차이 추출)
- 샘플 skeleton으로 실행 후 `femurToTorsoRatio`, `jointAngleBaselineDeg` 출력 확인

완료 기준: `BodyProfile`이 채워지고 구조적 baseline이 계산된다.

### Phase 3. 피처 추출 (`analysis_features.py`)

- `extract_features(clean_frames, body_profile)` 구현
- 관절 각도, hip 높이, `load_ratio` 계산
- timeseries JSON 직렬화 확인

완료 기준: `FeatureSet`이 채워지고 timeseries를 JSON으로 직렬화할 수 있다.

### Phase 3.5. CoP 분석 (`analysis_cop.py`)

- `GroundRef` 정의 및 `extract_ground_ref()` 구현 — 지면 Y, 발 중심 X 추출
- `detect_view()` 구현 — sagittal / frontal / unknown + confidence 산출
- `estimate_com()` 구현 — Winter 7분절 모델, 누락 랜드마크 fallback 처리
- `extract_cop()` 구현 — CoM → CoP 준정적 투영, 모멘트 암 계산
- `feature_set`에 CoP 시계열 채우기
- 측면뷰 샘플(`backSquat.mp4`)에서 `cop_ap_normalized` 시계열 육안 확인
  - 하강 시 값이 양수(앞)로 이동하는지, 최저점에서 안정적인지 검증
- 정면뷰 샘플이 있으면 `cop_ml_normalized` 좌우 편향이 직관과 맞는지 검증

완료 기준: `FeatureSet.cop_ap_normalized` 또는 `FeatureSet.cop_ml_normalized`가 view에 맞게 채워지고, 자동 탐지 confidence가 낮을 때는 CoP warning이 비활성화된다.

### Phase 4. Rep 분할 (`analysis_reps.py`)

- `detect_reps()` 구현
- backSquat.mp4 샘플(320프레임, 약 10초)에서 rep 수 육안 확인

완료 기준: `repSegments`가 비어 있지 않고 시작/종료/최저점이 타당하다.

### Phase 5. KPI + 이벤트 + 이슈 (`analysis_kpis.py`, `analysis_events.py`, `analysis_issues.py`)

- `calc_kpis(features, rep_segments, body_profile)` 구현 — `trunk_lean_excess`, `load_ratio_knee` 포함
- `detect_issues(features, rep_segments, kpis, body_profile)` 구현 — 체형 기반 상대 판정 확인
- `GET /jobs/{job_id}/result` 응답에서 전체 구조 확인

완료 기준: `analysis` 블록이 이 문서의 5절 스키마를 만족하고, 이슈 판정이 체형 비율을 참조한다.

### Phase 6. 스키마 타입 고정 (선택)

- `schema/result.py`에서 `analysis` 필드를 `dict`에서 typed Pydantic 모델로 전환
- 프론트엔드 계약 고정

완료 기준: `/docs`에서 `analysis` 응답 구조가 타입과 함께 표시된다.

---

## 10. 미결 사항

다음 항목은 이 문서의 범위 밖이며 별도로 정의해야 한다.

| 항목 | 현재 상태 | 후속 작업 |
|------|----------|----------|
| `expectedTrunkLean` 계산 공식 정밀화 | 현재 체형 + 세션 분포 기반 참조값 사용 | 운동 종류별 reference band 튜닝 필요 |
| 운동별 판정 항목 확장 | 이 문서에서는 squat 예시만 제시 | 운동 종류별 required joints, rep 탐지 기준, 이슈 룰 config 분리 |
| 멀티뷰 3D 재구성 | 미착수 | `service/reconstruction_3d.py` 신규 설계 |
| LLM 입력 포맷 | `service/llm_feedback.py`에서 별도 정의 | `bodyProfile` + `kpis` + `cop_kpis` + `issues`를 요약한 prompt builder 설계 |
| 운동 분류 자동화 | 현재 `exercise_type`을 클라이언트에서 넘김 | 추후 모델 기반 분류 가능 |
| 카메라 뷰 방향 자동 탐지 | MVP v1에서 자동 탐지로 통일 | 랜드마크 패턴 기반 confidence calibration 및 fallback 규칙 검증 |
| CoP 준정적 근사 한계 보정 | 현재 정적 근사만 적용 | 빠른 전환 구간에서 동적 항(가속도) 보정 — 신체 질량 입력이 있을 때 적용 가능 |
| 바벨 하중 정보 입력 | 현재 바벨 하중 미입력 | 사용자가 총 하중을 입력하면 절대 관절 토크(N·m) 추정 가능 |
