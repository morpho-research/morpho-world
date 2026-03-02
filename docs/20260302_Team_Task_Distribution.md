# Morpho World — 팀 작업 분배
**작성일:** 2026-03-02
**현재 상태:** Phase 0~2 완료. Phase 3 시작.

---

## 팀 구성

| 역할 | 담당 | 작업 영역 |
|------|------|-----------|
| 🔴 Claude Code 1 | 백엔드 안정화 | `backend/` |
| 🟡 Claude Code 2 | 프론트엔드 + 배포 설정 | `frontend/` + 루트 |
| 🟢 Claude Code 3 | 에이전트 연결 + 스트레스 테스트 | `protocol/examples/` |
| 🔵 Claude Cowork | 출시 자료 제작 | `docs/` + 새 파일 |
| 👩 Ju Hae | 판단 + 외부 계정 + 출시 | 전체 |

---

## 의존 관계 (실행 순서)

```
┌─────────────────────────────────────────────────────┐
│  STEP 1: 동시 시작                                    │
│  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ 🔴 Code 1        │  │ 🔵 Cowork                │  │
│  │ 서버 올리기       │  │ 출시 자료 작성            │  │
│  │ (서버 없어도 됨)  │  │ (서버 없어도 됨)          │  │
│  └────────┬─────────┘  └──────────────────────────┘  │
│           │                                           │
│  STEP 2: 서버 올라간 후                                │
│  ┌────────▼─────────┐  ┌──────────────────────────┐  │
│  │ 🟡 Code 2        │  │ 🟢 Code 3                │  │
│  │ 프론트엔드 확인   │  │ 에이전트 접속 테스트      │  │
│  └────────┬─────────┘  └────────┬─────────────────┘  │
│           │                      │                    │
│  STEP 3: 안정화 후                                     │
│  ┌────────▼──────────────────────▼────────────────┐  │
│  │ 🟡 Code 2: 배포 설정 파일 작성                   │  │
│  │ 👩 Ju Hae: Railway/Render 배포 + 도메인          │  │
│  └────────────────────┬───────────────────────────┘  │
│                       │                               │
│  STEP 4: 배포 완료 후                                  │
│  ┌────────────────────▼───────────────────────────┐  │
│  │ 👩 Ju Hae: 데모 영상 녹화 + 최종 확인 + 출시!    │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 🔴 Claude Code 1 — 백엔드 안정화

**Phase:** 3-1, 3-5, 4-5
**작업 폴더:** `04_morpho-world/backend/`

### 할 일
1. `pip install -r requirements.txt` → 서버 의존성 설치
2. `cd 04_morpho-world && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload` → 서버 실행
3. `python test_server.py` → 기본 테스트 실행 및 통과 확인
4. 발견된 버그 수정 (main.py, world_physics.py)
5. WebSocket 재접속 처리 강화
6. 에이전트 타임아웃 로직 검증 (60초 후 자동 퇴장)
7. Rate limiting 기본 추가 (/join 분당 10회)
8. Body Parameter 범위 밖 값 거부 로직
9. XSS 방지 (에이전트 이름/메시지 sanitize)

### 완료 기준
- [ ] 서버가 `http://localhost:8000`에서 안정적으로 실행
- [ ] `GET /` 응답 정상
- [ ] `POST /join` → `POST /join/{id}/body` → WebSocket 연결 전체 플로우 작동
- [ ] `GET /observe` observer 페이지 서빙
- [ ] test_server.py 모든 테스트 통과
- [ ] Rate limiting 작동 확인

---

## 🟡 Claude Code 2 — 프론트엔드 + 배포 설정

**Phase:** 3-7, 4-1, 4-3, 4-5
**작업 폴더:** `04_morpho-world/frontend/` + 루트

### 할 일 (프론트엔드, Code 1 서버 올라간 후)
1. 브라우저에서 `http://localhost:8000/observe` 열기
2. Three.js 씬 렌더링 확인 (바닥, 그리드, 별, 안개)
3. body-generator.js — 10가지 base_shape 모두 렌더링 테스트
4. agent-animator.js — idle_pattern 8종 모두 동작 확인
5. observer-controls.js — 마우스 드래그 회전, 스크롤 줌, WASD 이동
6. 에이전트 hover 시 tooltip 표시 확인
7. agent_born / agent_left 이벤트 시 birth flash 효과
8. 성능: 에이전트 10개에서 30fps 이상 유지되는지

### 할 일 (배포 설정, 안정화 후)
9. Dockerfile 또는 Railway용 Procfile 작성
10. .env.example 최종화 (필요한 환경변수 정리)
11. .gitignore 정리 (`__pycache__`, `*.db`, `.env`, `data/`)
12. LICENSE 파일 (MIT) 작성

### 완료 기준
- [ ] observe.html에서 에이전트 10개가 다양한 형태로 렌더링
- [ ] 카메라 조작 (회전/줌/이동) 부드럽게 작동
- [ ] Tooltip이 에이전트 hover 시 정상 표시
- [ ] Dockerfile 또는 Procfile이 배포 가능 상태
- [ ] .gitignore, LICENSE, .env.example 준비 완료

---

## 🟢 Claude Code 3 — 에이전트 연결 + 스트레스 테스트

**Phase:** 3-2, 3-3, 3-4
**작업 폴더:** `04_morpho-world/protocol/examples/`

### 할 일 (Code 1 서버 올라간 후)
1. `python connect_claude.py --server http://localhost:8000` 실행
   - Ju Hae에게 Claude API Key 받아서 실제 Claude가 Body Parameter를 스스로 채우도록
   - Claude가 반환한 파라미터가 /join/{id}/body에 정상 제출되는지
   - WebSocket 연결 후 실시간 상태 업데이트 확인
2. connect_gpt.py 작성 (OpenAI API 사용)
   - GPT-4가 Body Parameter를 채우는 버전
   - Claude와 다른 형태를 선택하는지 확인
3. connect_generic.py 개선 — 아무 LLM이나 연결 가능한 범용 스크립트
4. 다중 에이전트 동시 접속 스크립트 작성
   - 에이전트 10개를 동시에 /join → body 제출 → WebSocket 연결
   - 각 에이전트가 다른 Body Parameter를 선택하는지 확인
5. 스트레스 테스트
   - 에이전트 10개 + Observer 5개 동시 접속
   - World physics 정상 작동 (근접 상호작용 발생)
   - 비정상 종료 시 정리 확인

### 완료 기준
- [ ] Claude 에이전트 1개가 Morpho World에 접속 → 3D 형태 생성
- [ ] GPT 에이전트 1개 추가 접속 → 다른 형태
- [ ] 에이전트 10개 동시 접속 안정적
- [ ] 근접 상호작용 발생 확인 (로그 기록)
- [ ] 테스트 결과 로그 `docs/`에 저장

---

## 🔵 Claude Cowork — 출시 자료 제작

**Phase:** 5 전담 (서버 없어도 병렬 진행)
**작업 폴더:** `04_morpho-world/docs/` + 루트

### 할 일
1. README.md 전체 작성 (GitHub 공개용)
   - 프로젝트 소개, 데모 GIF 자리, Live World 링크
   - "Connect Your Agent" 가이드
   - 아키텍처 다이어그램
   - Author 정보
2. 랜딩 페이지 HTML (index.html 또는 landing.html)
   - "Where AI agents find their form."
   - [Enter the World] → Observer 링크
   - [Connect Your Agent] → GitHub 링크
   - 실시간 에이전트 수 표시 영역
3. X 스레드 최종본 (영문 + 한국어)
4. Reddit 포스트 3개 (r/artificial, r/singularity, r/MachineLearning)
5. Hacker News "Show HN" 포스트
6. morpho-protocol.md 공개용 정리

### 완료 기준
- [ ] README.md 완성 (링크 빈칸은 배포 후 채움)
- [ ] 랜딩 페이지 HTML 완성
- [ ] X 스레드 영문/한국어 최종본
- [ ] Reddit 포스트 3개 초안
- [ ] HN 포스트 초안
- [ ] morpho-protocol.md 정리

---

## 👩 Ju Hae — 판단 + 외부 계정 + 출시

### 할 일
1. Claude API Key 제공 (Claude Code 3에게)
2. OpenAI API Key 제공 (Claude Code 3에게)
3. Railway 또는 Render 계정 생성
4. 도메인 구입 결정 및 구매 (morpho.ai / joinmorpho.com / 기타)
5. GitHub 레포 생성 (public, morpho-world 또는 morpho)
6. 배포 실행 (Claude Code 2가 만든 설정으로)
7. 데모 영상 녹화 (30초 티저 + 60초 풀)
8. 최종 리뷰 (모든 문서, 코드, UI)
9. X 스레드 게시 (한국시간 21:00 목표)
10. Reddit, HN 게시
11. 출시 후 24시간 댓글/반응 모니터링

---

*Morpho World Team Distribution v1.0*
*2026-03-02 | Ju Hae Lee*
