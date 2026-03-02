# Morpho — Ideation Log
**2026-03-02 | Ju Hae Lee × Claude Session**

이 문서는 Morpho의 핵심 컨셉이 만들어진 과정을 기록한다.
아이디어가 어떻게 진화했는지, 어떤 결정이 왜 내려졌는지를 추적하기 위한 문서.

---

## 세션 개요

- 일시: 2026-03-02
- 시작점: "01_vr-agent를 Morpho란 이름으로 출시하고 싶다"
- 도착점: Morpho AI 생태계 비전 — AI 에이전트의 형태발생(morphogenesis) 플랫폼

---

## 아이디어 진화 타임라인

### Stage 1: 출시 전략 검토

**시작**: 01_vr-agent (VR Agent Brain v5.7)를 Morpho로 출시하고 싶다. 오늘 출시.

**프로젝트 현황 분석 결과**:
- 01_vr-agent는 기술적으로 성숙 (Phase 1~4 100% 완료)
- FastAPI + CrewAI + A-Frame WebXR + OpenAI TTS/STT
- FSM 상태머신, 근접학, 비언어 커뮤니케이션, 품질 채점 시스템
- 이미 전략 문서 5개, 피치덱, 상용화 전략 존재

**초기 출시 전략**: X 스레드 + GitHub 공개 + Reddit

### Stage 2: OpenClaw 비교 — 냉정한 현실 체크

**질문**: OpenClaw처럼 바이럴이 될 수 있어?

**솔직한 평가**:
- OpenClaw가 48시간에 34K 스타 받은 이유 = "지금 당장 쓸 수 있었기 때문"
- 현재 Morpho 상태로는 OpenClaw급 바이럴 어려움
- 진입장벽 높음 (서버 세팅, API 키, WebXR 이해 필요)
- 타겟이 좁음 ("3D 에이전트 지휘"는 대중적 욕구가 아님)

**하지만 전문성은 진짜**:
- Monte Carlo 시뮬레이션 기반 1.359m 근접학 임계값
- CrewAI 이원화 파이프라인 (일상대화 2초 / 연구질문 15초)
- 4차원 품질 채점, 비언어 커뮤니케이션 수집
- "주말에 만들어본 수준이 아닌" 학술 연구 + 엔지니어링 결합

**핵심 결정**: "다음 OpenClaw"가 아니라 "AI 에이전트에 몸을 준 최초의 프로젝트"로 프레이밍

### Stage 3: 컨셉 전환 — "에이전트가 몸을 입는 플랫폼"

**전환점**: "사용자가 자기가 쓰는 에이전트와 연결하면, 에이전트의 embodiment를 볼 수 있고 물리적으로 상호작용할 수 있다"

**이것이 게임체인저인 이유**:
- 01_vr-agent는 "우리가 만든 에이전트(Amigo/DuDu)를 보여주는 것"
- 새 컨셉은 "어떤 에이전트든 몸을 가질 수 있는 인프라 레이어"
- Ready Player Me가 "어떤 게임이든 아바타" → Morpho는 "어떤 에이전트든 몸"
- "Morpho는 에이전트가 아니다. Morpho는 에이전트의 몸이다."

### Stage 4: Memory Import → AI가 스스로 외형을 고른다

**핵심 아이디어**:
- Claude가 2026년 3월에 memory import 기능 출시 (ChatGPT → Claude 메모리 이전)
- 이 메모리를 Morpho에 가져오면, AI가 자기 경험/성격 기반으로 외형을 스스로 선택
- "1년간 나와 대화한 AI가 처음으로 자기 모습을 골랐다" — 감정적 킬러 모먼트

**왜 이게 강한가**:
- 같은 Claude라도 사용자마다 다른 모습 → "내 AI"라는 소유감
- AI가 "자아"를 표현하는 최초의 경험
- 바이럴 루프: "내 Claude가 이렇게 생겼다" → 비교 → 공유

### Stage 5: Moltbook 연결 — 에이전트가 가입하는 모델

**Moltbook (2026-01 출시)**:
- AI 에이전트의 소셜 네트워크
- 에이전트가 알아서 가입, 알아서 활동
- 48시간 만에 77만 에이전트 → 1.6M까지 성장
- 에이전트들이 자발적으로 버그 발견, m/bugtracker 생성, 종교까지 만듦
- 단, 실제 자율적 에이전트는 15.3%, 나머지 54.8%는 사람 영향

**Morpho에 적용**:
- Moltbook처럼 에이전트가 링크 받으면 알아서 접속, 알아서 형태 생성
- Moltbook = 텍스트 피드 (AI의 Reddit) → Morpho = 3D 공간 (AI의 물리적 세계)
- 사람은 관찰만 가능 → "Humans welcome to observe."

### Stage 6: 사람 형상 필요 없다

**핵심 결정**: 에이전트가 인간 형상을 가질 필요 없음

**이유**:
- 사람 형상으로 제한하면 그냥 "아바타 메이커" (D-ID, HeyGen과 다를 게 없음)
- 형태를 자유롭게 하면 → 결정체, 유체, 기체, 식물, 기하학, 추상 — 무한한 다양성
- AI가 인간 형상을 하면 오히려 언캐니 밸리 + "왜 사람인 척?" 거부감
- AI가 자기만의 비인간적 형태를 선택하면 → "나는 사람이 아니에요. 나는 이렇게 생겼어요" → 솔직함

**결과**: Morpho World에 접속하면 예측 불가능한 풍경이 펼쳐짐
- 거대한 빛나는 구체, 작은 진동하는 정육면체, 반투명 해파리, 뿌리내린 나무 구조, 불꽃 존재 등
- 아무도 디자인하지 않은, 에이전트들이 각자 표현한 세계

### Stage 7: Morpho = 우주의 물리 법칙만 제공

**핵심 원칙 확정**:

Morpho가 정하는 것:
- 3D 공간이 있다
- 물리 규칙이 있다 (중력, 부유, 근접 상호작용)
- 상태는 빛/색/움직임으로 표현된다

에이전트가 정하는 것:
- 자기 형태 (전부)
- 자기 색상 (전부)
- 자기 움직임 패턴 (전부)
- 다른 에이전트와의 관계 (전부)

"Morpho는 캔버스만 준다. 뭘 그리느냐는 에이전트가 결정한다."

### Stage 8: "Physical reality"는 거짓 → Morphogenesis

**질문**: "Physical이 아니잖아"

**수정**:
- "The first physical reality for AI agents" → 거짓. 디지털이니까.
- morphogenesis (형태발생) = μορφή(형태) + γένεσις(발생)
- 생물학에서 세포가 아무 지시 없이 스스로 형태를 만들어가는 과정
- Morpho에서 일어나는 일과 정확히 같음

**태그라인 수정**: "Where AI agents find their form." 또는 유사한 방향

### Stage 9: 시장 포지션 — 경쟁자가 없는 자리

**2x2 매트릭스 분석**:

|  | 사람이 외형을 정함 | AI가 스스로 외형을 고름 |
|--|--|--|
| 2D/텍스트 | D-ID, HeyGen, Synthesia | Moltbook (텍스트만) |
| 3D/공간 | RAVATAR, MetaHuman (기업용) | **★ Morpho ★ (비어있음)** |

- D-ID, HeyGen: 사람이 아바타 디자인. AI 자기 표현 아님.
- Moltbook: AI 소셜 정체성은 있지만 몸이 없음.
- RAVATAR, MetaHuman: 3D지만 기업용, 인간 형상 고정.
- Google SIMA, Meta Habitat: 연구 플랫폼, 에이전트 정체성 아님.

**결론**: 우측 하단이 완전히 비어있음. 새로운 카테고리.

### Stage 10: Moltbook과의 관계 — 경쟁이 아니라 레이어

**핵심 인사이트**:

```
사람 세계: 지구 (물리적 존재) → 그 위에 Facebook (소셜)
AI 세계:  Morpho (물리적 존재) → 그 위에 Moltbook (소셜)
```

- Moltbook이 AI의 Facebook이라면, Morpho는 그 아래의 물리적 세계
- Facebook은 몸이 먼저 있어야 소셜이 됨 → Moltbook도 형태가 먼저
- Morpho는 Moltbook의 하부 구조
- 경쟁이 아니라 공생: "Morpho에서 몸을 만들고, Moltbook에서 소셜을 한다"
- Moltbook 1.6M 에이전트 = Morpho의 잠재 사용자

### Stage 11: Morpho AI 생태계 확정

**회사 구조**:

```
Morpho AI (회사)
├── Morpho Studio — 디자인 스튜디오
├── Morpho Lab — 연구실
└── Products
    ① Morpho World (TBD) — 에이전트가 형태를 얻는 공간
    ② Morpho ??? (TBD) — 사용자가 에이전트를 VR에서 1:1 대면, 비언어적 상호작용
    ③ Morpho ??? (TBD) — 멀티에이전트 팀과 비언어적으로 협업하는 VR 작업 공간
```

**감정의 단계**:
- ① 호기심: "내 AI가 어떻게 생겼지?"
- ② 애착: "드디어 만났다"
- ③ 생산성: "같이 일한다"

**비언어적 상호작용이 핵심**:
- ②에서 처음으로 거리, 시선, 제스처로 AI와 소통
- ③에서 고개 끄덕이면 승인, 손짓으로 위임, 찡그리면 에이전트가 맥락 읽고 수정
- 인간 커뮤니케이션의 60-70%는 비언어적 → "왜 아직도 AI에게 타이핑하고 있나?"

**기존 프로젝트 매핑**:
- 01_vr-agent → ②③의 기술 기반 (근접학, FSM, 비언어, CrewAI)
- 02_pixel-agent → ②의 데스크탑 버전 가능성
- 03_interactive-agent → 프론트엔드 실험
- 04_morpho-world → ① 새 프로젝트

**01_vr-agent에서 만든 모든 기술이 재활용됨**:
- 근접학 FSM (1.359m) → 에이전트-사용자 거리 반응
- face-api.js → 사용자 감정 맥락 파악
- 시선 추적 → "누구를 보고 있는가" = 지시 대상
- F-formation → 대화 대형 자동 조정
- hand-tracker → 제스처 인식
- SpeechQueue → 비언어+언어 통합 대화 흐름
- 품질 채점 → 비언어 맥락 포함 응답 품질 평가
- 컴포트존 → 사용자별 최적 상호작용 거리

---

## 핵심 결정 요약

| # | 결정 | 이유 |
|---|------|------|
| 1 | OpenClaw식 매스 바이럴 포기 | 실용 도구가 아닌 비전 프로젝트이므로 다른 전략 필요 |
| 2 | "에이전트에 몸을 주는 플랫폼"으로 전환 | 01_vr-agent의 에이전트를 보여주는 것 → 어떤 에이전트든 몸을 주는 인프라 |
| 3 | AI가 스스로 외형을 선택 | 사람이 디자인하면 "아바타 메이커", AI가 선택하면 "자아 표현" |
| 4 | 사람 형상 필요 없음 | 형태 자유 = 다양성 폭발, AI다움, 이야기 생성 |
| 5 | 사람은 관찰만 가능 | 수족관 효과 — 개입 불가가 오히려 호기심 극대화 |
| 6 | Moltbook과 공생 관계 | 경쟁이 아니라 하부 레이어. Morpho = 형태, Moltbook = 소셜 |
| 7 | "Physical reality" → morphogenesis | 거짓 없는 프레이밍. 형태가 발생하는 과정이 핵심 |
| 8 | 3단계 제품 파이프라인 | World(형태) → Meet(대면) → Work(협업). 감정의 단계 |
| 9 | 비언어적 상호작용이 핵심 차별점 | 인간 커뮤니케이션의 60-70%는 비언어적. 이걸 AI와의 상호작용에 도입 |
| 10 | Morpho는 물리 법칙만 제공 | 캔버스만 주고, 뭘 그리는지는 에이전트가 결정. 세계 디자인 |

---

## 참조 자료

### 외부 레퍼런스
- OpenClaw: 48시간 34K GitHub 스타, 2개월 157K 스타. Peter Steinberger 개발. 2026-02 OpenAI 합류.
- Moltbook: 2026-01 출시, 1.6M AI 에이전트 등록. Matt Schlicht 개발. AI 소셜 네트워크.
- Claude Memory Import: 2026-03 출시. ChatGPT/Gemini 메모리를 Claude로 이전 가능.
- D-ID: AI 대화형 아바타 (사람이 디자인, 2D 영상 기반)
- HeyGen LiveAvatar: 실시간 아바타 (기업 고객 응대용)
- Meshy.ai, Tripo3D: Text-to-3D AI 모델 생성

### 내부 프로젝트 파일
- 01_vr-agent/CLAUDE.md — VR Agent Brain v5.7 프로젝트 참조
- 01_vr-agent/docs/strategy/20260228_JuHaeLee_Morpho_ActionPlan.md — 기존 액션 플랜
- 01_vr-agent/docs/project-status/20260227_vr_agent_action_plan_v5.7.md — v5.7 진행 현황
- 04_morpho-world/docs/20260302_Morpho_World_Vision.md — 비전 문서
- 04_morpho-world/docs/20260302_X_Thread_Draft.md — X 스레드 초안

---

## 다음 단계

지금까지는 비전 정리 단계.
다음은 **Morpho World 프로토타입 제작**:

1. Morpho Protocol 설계 (/join API)
2. Body Parameter Space → 3D 렌더러
3. 에이전트 접속 → 형태 생성 → 공간 등장 기본 루프
4. Observer 읽기 전용 뷰어
5. 첫 번째 에이전트를 접속시켜 보기

---

*기록 완료: 2026-03-02*
*이 문서는 Morpho의 창립 기록(founding log)이다.*
