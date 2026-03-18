[feature] MediaPipe Python 기반 백엔드 PoseLandmarker 구현

브랜치명: `feature/8-mediapipe-python-poselandmarker-backend`

feat: MediaPipe Python 기반 백엔드 PoseLandmarker 초기 구현 (#8)

- MediaPipe Python 기반 PoseLandmarker 실행 환경과 백엔드 모듈 구조를 구성한다.
- 이미지/비디오 입력 처리와 포즈 랜드마크 추론 로직을 구현한다.
- 추론 결과를 JSON 형태로 직렬화하고 예외 처리 흐름을 정리한다.

[feature] MediaPipe Python 기반 백엔드 PoseLandmarker 구현 (#8)

## 관련 Issue
Closes #8

## 작업 내용
- MediaPipe Python 솔루션을 이용한 백엔드용 PoseLandmarker 모듈을 구현한다.
- 업로드된 이미지 또는 비디오 파일을 입력으로 받아 포즈 랜드마크를 추출할 수 있도록 처리한다.
- 추론 결과를 백엔드에서 재사용 가능한 JSON 구조로 정리한다.
- 추후 API 서버 또는 서비스 레이어에 연결하기 쉽도록 실행 로직과 입출력 포맷을 분리한다.

## 변경 사항 상세
- Python 환경에서 MediaPipe Tasks Vision PoseLandmarker를 로드하고 추론하는 기본 구조를 추가한다.
- 입력 파일 검증, 프레임 처리, 추론 수행, 결과 직렬화까지의 백엔드 파이프라인을 정의한다.
- 랜드마크 좌표, 프레임 메타데이터, 에러 응답 포맷을 일관된 형태로 반환하도록 설계한다.
- 로컬 개발 및 검증을 위한 실행 예제 또는 테스트 스크립트를 포함한다.

## 테스트 방법
1. 백엔드 실행 환경에서 PoseLandmarker 모듈을 실행한다.
2. 샘플 이미지 또는 비디오 파일을 입력으로 전달한다.
3. 포즈 랜드마크 결과가 지정한 JSON 구조로 생성되는지 확인한다.
4. 잘못된 파일 형식이나 누락된 입력에 대해 예외 처리가 정상 동작하는지 확인한다.

## 스크린샷 / 결과
- MediaPipe Python 기반 백엔드 PoseLandmarker 추론 결과 JSON 확인
- 정상 입력과 예외 입력에 대한 실행 결과 로그 확인
