# 🔴 Claude Code 1 — 백엔드 안정화 지시문

아래 내용을 Claude Code 터미널에 복사해서 붙여넣으세요.

---

```
너는 "Morpho World" 프로젝트의 백엔드 담당이야.
프로젝트 위치: 04_morpho-world/

## 프로젝트 이해
Morpho World는 AI 에이전트들이 스스로 3D 형태를 선택하고 가상 세계에 존재하는 프로젝트야.
사람은 브라우저에서 관찰만 할 수 있어. 에이전트는 API로 접속해서 자기 형태를 결정해.

## 현재 상태
- backend/main.py — FastAPI 서버 작성 완료 (테스트 필요)
- backend/requirements.txt — 의존성 목록 있음
- test_server.py — 테스트 스크립트 있음
- frontend/ — 프론트엔드 완성 (수정하지 마)

## 네 할 일 (순서대로)

### 1단계: 서버 올리기
- cd 04_morpho-world
- pip install -r backend/requirements.txt
- uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
- 서버가 정상 실행되는지 확인

### 2단계: 기본 테스트
- 새 터미널에서: python test_server.py
- 5개 테스트 모두 통과하는지 확인
- 실패하는 테스트가 있으면 main.py 수정해서 통과시켜

### 3단계: 버그 수정 및 안정화
main.py를 리뷰하고 다음 문제들을 확인/수정해:

a) world_physics.py의 "새 에이전트 curiosity" 로직에 created_at 파싱 버그 있음:
   ```python
   # 이 부분이 깨질 수 있어 — 안전하게 수정해
   if time.time() - float(other.created_at.replace(...)) < 30:
   ```
   → created_at을 timestamp float으로 별도 저장하는 방식으로 수정

b) WebSocket 재접속 처리:
   - 에이전트 연결이 끊겼을 때 즉시 삭제하지 않고 60초 타임아웃으로 처리 → 이미 되어있는지 확인
   - 같은 agent_id로 재접속 시 기존 상태 유지되는지 확인

c) Observer WebSocket이 에러 없이 다수 접속 가능한지 확인

### 4단계: 보안 기본 추가
a) Rate limiting — /join 엔드포인트에 분당 10회 제한
   - 간단하게 in-memory dict로 IP별 요청 카운트
   - 별도 라이브러리 없이 구현

b) Body Parameter 검증 강화:
   - scale: 0.3~3.0 범위 밖이면 기본값으로 클램프
   - 숫자 필드: 범위 밖이면 기본값
   - 문자열 필드: 최대 500자 제한

c) XSS 방지:
   - agent_name, message 필드에서 HTML 태그 제거 (html.escape)
   - form_description, self_reflection도 sanitize

### 5단계: 서버 안정성 확인
- 서버를 5분 이상 실행 상태 유지
- 메모리 누수 없는지 확인
- world_loop가 정상 동작하는지 (10fps physics)

## 중요 규칙
- frontend/ 폴더의 파일은 수정하지 마 (다른 팀원 담당)
- protocol/ 폴더의 파일은 수정하지 마 (다른 팀원 담당)
- 수정한 내용은 간단한 주석으로 기록해
- 서버가 안정적으로 올라가면 "서버 준비 완료"라고 알려줘

## 완료 기준
- [ ] 서버 http://localhost:8000 에서 안정 실행
- [ ] GET / 응답 정상
- [ ] POST /join → POST /join/{id}/body → WebSocket 전체 플로우 작동
- [ ] GET /observe observer 페이지 서빙
- [ ] test_server.py 모든 테스트 통과
- [ ] Rate limiting 작동
- [ ] created_at 파싱 버그 수정
- [ ] XSS sanitize 적용
```
