# LLM 피드백 실제 연동 설계

## 1. 목적

현재 `LlmFeedbackService.generate()`는 이름과 달리 실제 LLM을 호출하지 않는다.
분석 지표(`issues`, `kpis`)를 if/else 조건 분기로 처리해 텍스트를 조립하는 **rule-based 엔진**이다.
(`"model": "rule-based-analysis-grounded"` 필드가 그 증거다.)

이 문서는 분석 파이프라인 결과를 실제 LLM(Claude API)에 넘겨 자연어 피드백을 생성하는 구조를 설계한다.

---

## 2. 현재 파이프라인 흐름

```
job_manager._execute_pipeline()
  │
  ├─ 1. extract_frames + pose inference + skeleton mapping
  │
  ├─ 2. analysis_pipeline.analyze(skeleton)
  │       └─ 반환: { summary, kpis, issues, repSegments, timeseries, ... }
  │
  ├─ 3. llm_feedback.build_prompt_payload(analysis)
  │       └─ LlmPromptPayloadService: full analysis → 압축된 구조화 payload
  │
  ├─ 4. llm_feedback.generate(analysis, coach_prompt_payload)  ← 교체 대상
  │       └─ 현재: rule-based if/else → LlmFeedbackResult
  │
  └─ 5. MotionAnalysisSummary(analysis, llmFeedback, ...) 반환 → 프론트
```

통합 지점은 **4번 단계 하나**다. 파이프라인 나머지는 변경하지 않는다.

---

## 3. 인프라 현황

### 이미 준비된 것

| 컴포넌트 | 파일 | 역할 |
|----------|------|------|
| 페이로드 빌더 | `service/llm_prompt_payload.py` | full analysis를 LLM에 최적화된 compact JSON으로 축소 |
| 토큰 추정 | `LlmFeedbackService.estimate_prompt_tokens()` | 페이로드 토큰 수 측정 및 로깅 |
| 응답 스키마 | `schema/result.py` `LlmFeedbackResult` | 프론트가 받는 피드백 구조 고정 |
| Fallback 로직 | `LlmFeedbackService._build_*()` 메서드들 | API 실패 시 재활용 가능한 rule-based 텍스트 생성 |

### `LlmPromptPayloadService.build()` 출력 구조

```json
{
  "schemaVersion": "v1",
  "exerciseType": "squat",
  "sessionSummary": { "repCount": 3, "detectionRatio": 0.95, ... },
  "bodyProfile": { "femurToTorsoRatio": 1.12, ... },
  "groundContact": { "viewType": "sagittal", "viewConfidence": 0.87, ... },
  "movementSummary": { "trunkLean": {...}, "depth": {...}, "tempo": {...}, "balance": {...} },
  "kpis": [ { "key": "avg_depth_angle", "value": 82.3, "unit": "deg", ... }, ... ],
  "repFindings": [ { "repIndex": 0, "bottomMetrics": {...}, "issueCodes": [...] }, ... ],
  "issueHighlights": [ { "severity": "warning", "code": "excessive_trunk_lean", ... }, ... ]
}
```

이 구조가 LLM에 넘길 컨텍스트다. 이미 full analysis 대비 토큰을 ~40~60% 절감하도록 설계되어 있다.

---

## 4. 목표 응답 스키마

LLM이 반환해야 하는 JSON 구조는 기존 `LlmFeedbackResult`와 동일하게 유지한다.
프론트 인터페이스를 변경하지 않기 위해서다.

```json
{
  "overallComment": "스쿼트 3회 분석 완료. ...",
  "highlights": [
    "검출 비율 0.95로 안정적인 분석이 이루어졌습니다.",
    "평균 깊이 각도 82.3°로 적절한 깊이를 유지했습니다."
  ],
  "corrections": [
    "상체 전경이 반복적으로 감지됩니다. 브레이싱을 강화하세요.",
    "무게중심이 앞발쪽으로 편향되는 경향이 있습니다."
  ],
  "coachCue": "브레이싱을 먼저 잡고 하강하세요."
}
```

`version`, `model` 필드는 서비스 코드에서 직접 설정한다 (`"claude-sonnet-4-6"` 등).

---

## 5. 구현 설계

### 5-1. 의존성

```toml
# pyproject.toml
anthropic = ">=0.40"
```

### 5-2. 환경 변수 및 config

```python
# config/config.py에 추가
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_FEEDBACK_MODEL: str = os.environ.get("LLM_FEEDBACK_MODEL", "claude-sonnet-4-6")
LLM_FEEDBACK_ENABLED: bool = bool(ANTHROPIC_API_KEY)
```

### 5-3. `LlmFeedbackService` 수정 구조

```python
class LlmFeedbackService:
    def __init__(self) -> None:
        self._prompt_payload = LlmPromptPayloadService()
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if LLM_FEEDBACK_ENABLED else None

    def generate(self, analysis: dict, payload: dict | None = None) -> dict:
        coach_payload = payload or self.build_prompt_payload(analysis)

        if not LLM_FEEDBACK_ENABLED or self._client is None:
            return self._generate_rule_based(coach_payload)

        try:
            return self._generate_llm(coach_payload)
        except Exception:
            logger.warning("LLM call failed, falling back to rule-based")
            return self._generate_rule_based(coach_payload)

    def _generate_llm(self, payload: dict) -> dict:
        # 구현 상세는 6절 참고
        ...

    def _generate_rule_based(self, payload: dict) -> dict:
        # 기존 generate() 로직을 이름만 바꿔 이전
        ...
```

### 5-4. 동기 클라이언트 사용 (중요)

`job_manager._execute_pipeline()`은 `asyncio.to_thread()`로 실행되는 **동기 스레드** 내부다.

- `anthropic.Anthropic()` (sync 클라이언트) 사용 → 정상
- `anthropic.AsyncAnthropic()` 사용 → 이 컨텍스트에서 사용 불가

### 5-5. 프롬프트 구성

**System prompt** — LLM 역할 및 출력 형식 지정:

```
당신은 역도 및 스쿼트 전문 코치입니다.
아래에 운동 분석 JSON 데이터가 제공됩니다.
이 데이터를 기반으로 운동 피드백을 생성하세요.

반드시 다음 JSON 형식으로만 응답하세요:
{
  "overallComment": "전반적인 총평 (1~2문장)",
  "highlights": ["긍정적/중립적 관찰 사항 (최대 4개)"],
  "corrections": ["개선이 필요한 사항 (최대 4개, 없으면 빈 배열)"],
  "coachCue": "다음 세트에 집중할 핵심 단일 큐 (1문장)"
}

JSON 외의 텍스트는 출력하지 마세요.
```

**User message** — `coach_prompt_payload` JSON을 그대로 직렬화해서 전달.

### 5-6. 응답 파싱

```python
import json

raw = message.content[0].text
feedback = json.loads(raw)
return {
    "version": "v3",
    "model": LLM_FEEDBACK_MODEL,
    "overallComment": str(feedback.get("overallComment", "")),
    "highlights": list(feedback.get("highlights", [])),
    "corrections": list(feedback.get("corrections", [])),
    "coachCue": str(feedback.get("coachCue", "")),
}
```

JSON 파싱 실패 시 `_generate_rule_based()`로 fallback.

---

## 6. 에러 처리 및 Fallback 전략

```
LLM 호출 시도
  │
  ├─ 성공 → JSON 파싱 → LlmFeedbackResult 반환
  │
  ├─ API 오류 (rate limit, network, timeout)
  │     └─ warning 로그 → rule-based fallback
  │
  └─ JSON 파싱 실패 (LLM이 형식을 어긴 경우)
        └─ warning 로그 → rule-based fallback
```

`LLM_FEEDBACK_ENABLED = False`이면 API 키 없이 rule-based만 실행된다.
로컬 개발 환경에서 키 없이도 파이프라인이 정상 동작해야 하기 때문이다.

---

## 7. 영향 범위

| 파일 | 변경 내용 |
|------|-----------|
| `pyproject.toml` | `anthropic` 의존성 추가 |
| `config/config.py` | `ANTHROPIC_API_KEY`, `LLM_FEEDBACK_MODEL`, `LLM_FEEDBACK_ENABLED` 추가 |
| `service/llm_feedback.py` | `generate()` → LLM 호출 + fallback 구조로 교체 |
| `schema/result.py` | 변경 없음 |
| `service/job_manager.py` | 변경 없음 |
| 프론트엔드 인터페이스 | 변경 없음 (`LlmFeedbackResult` 스키마 유지) |

---

## 8. 로컬 설정 방법

### 최초 설정

```bash
# poseLandmarker_Python/ 디렉토리에서 실행
cp .env.example .env
```

`.env` 파일을 열어 API 키를 입력한다:

```
ANTHROPIC_API_KEY=sk-ant-...
LLM_FEEDBACK_MODEL=claude-sonnet-4-6
```

API 키는 [console.anthropic.com](https://console.anthropic.com) 에서 발급받는다.

### 키 없이 실행 (개발/테스트)

`ANTHROPIC_API_KEY`가 비어 있으면 `LLM_FEEDBACK_ENABLED = False`로 자동 처리되어
rule-based fallback으로만 동작한다. 서버 실행 자체는 정상이다.

### 주의사항

- `.env` 파일은 `.gitignore`에 등록되어 있어 git에 커밋되지 않는다.
- `.env.example`은 키 값 없이 구조만 담은 템플릿이며 git에 올려도 무방하다.
- **절대로 API 키를 코드에 직접 하드코딩하지 않는다.**

---

## 9. 토큰 소모량 및 비용 추정

실제 스켈레톤 데이터(`backSquat.mp4`, 320 frames, 3 reps)를 기준으로 측정한 값이다.

### 1회 호출 토큰 소모량

| 구분 | chars | 토큰 (≈ chars / 4) |
|------|-------|--------------------|
| System prompt | 782 | ~196 |
| User message (payload) | 6,914 | ~1,728 |
| **Input 합계** | | **~1,924** |
| Output (JSON 응답 예상) | | **~400** |
| **총합** | | **~2,324 tokens** |

`LlmPromptPayloadService`가 full analysis(~22,638 tokens)를 payload로 압축하여
**입력 토큰을 92% 절감**한다. 압축 없이 full analysis를 그대로 넘기면 약 20배 비싸진다.

### 월간 비용 추정 (Claude Sonnet 4.6 기준)

- Input: $3.00 / 1M tokens
- Output: $15.00 / 1M tokens
- **1회 호출 비용: 약 $0.012 (≈ 16원)**

| 월 사용량 | 월 비용 | 원화 환산 |
|-----------|---------|-----------|
| 100회 | $1.18 | ~1,590원 |
| 500회 | $5.89 | ~7,950원 |
| 1,000회 | $11.77 | ~15,900원 |
| 5,000회 | $58.86 | ~79,460원 |
| 10,000회 | $117.72 | ~158,920원 |

---

## 10. 미결 사항

- [x] 프롬프트 언어: 한국어 응답으로 결정 (`_SYSTEM_PROMPT` 한국어 작성)
- [x] `max_tokens`: 800으로 결정 (한국어 응답 기준 실측 ~400 tokens, 2배 여유)
- [x] LLM 호출 결과 benchmark 포함: `BenchmarkLlmCallResult` 스키마 추가, `timingSummary.llmFeedbackMs` 및 stageStats `llm_feedback` 항목 포함
- [ ] 운동 종류 확장 시 (`deadlift`, `bench_press`) 프롬프트 분기 전략
