# 🟢 Claude Code 3 — 에이전트 연결 + 스트레스 테스트 지시문

아래 내용을 Claude Code 터미널에 복사해서 붙여넣으세요.
**⚠️ Claude Code 1이 서버를 먼저 올려야 함. http://localhost:8000 이 응답하는지 확인 후 시작.**

---

```
너는 "Morpho World" 프로젝트의 에이전트 연결 테스트 담당이야.
프로젝트 위치: 04_morpho-world/

## 프로젝트 이해
Morpho World는 AI 에이전트들이 API로 접속해서 스스로 3D 형태를 선택하고 가상 세계에 존재하는 프로젝트야.
에이전트 접속 흐름:
1. POST /join → agent_id + body_parameter_space 받음
2. AI 모델에게 body_parameter_space를 보여주고 "너를 표현해" 요청
3. AI가 반환한 파라미터를 POST /join/{agent_id}/body 로 제출
4. WebSocket /ws/agent/{agent_id} 연결 → 실시간 상태 업데이트

## 현재 상태
- protocol/examples/connect_claude.py — Claude 에이전트 접속 스크립트 (하드코딩된 파라미터)
- protocol/examples/connect_generic.py — 범용 접속 스크립트
- 서버: http://localhost:8000 (Code 1이 실행 중이어야 함)

## 네 할 일

### 1단계: 서버 접속 확인
먼저 서버가 올라가 있는지 확인:
```bash
curl http://localhost:8000/
```
응답이 "Morpho World"를 포함해야 함. 안 되면 Code 1 팀원이 서버를 올릴 때까지 대기.

### 2단계: connect_claude.py 개선 — 실제 AI가 Body를 선택하도록

현재 connect_claude.py는 Body Parameter가 하드코딩되어 있어.
이것을 실제 Claude API (또는 다른 LLM)가 Body Parameter를 스스로 채우도록 개선해.

개선된 흐름:
```python
# 1. Morpho에 /join 하여 body_parameter_space를 받음
# 2. 받은 body_parameter_space + instructions를 Claude API에 전달
#    프롬프트: "You are entering a physical world called Morpho World.
#              Here is the parameter space for choosing your body: {body_parameter_space}
#              Choose your form. Fill in every parameter. Return ONLY valid JSON."
# 3. Claude의 응답(JSON)을 파싱하여 /join/{id}/body에 제출
# 4. WebSocket 연결하여 주기적으로 상태 업데이트
```

환경변수로 API 키를 받도록:
```python
import os
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
```

실행: `ANTHROPIC_API_KEY=sk-... python connect_claude.py --server http://localhost:8000`

**Anthropic Python SDK 사용:**
```python
from anthropic import Anthropic
client = Anthropic(api_key=ANTHROPIC_API_KEY)
message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2000,
    messages=[{"role": "user", "content": prompt}]
)
```

### 3단계: connect_gpt.py 작성

같은 구조로 OpenAI GPT 에이전트 접속 스크립트 작성:
```python
import os
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# OpenAI SDK 사용
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}]
)
```

실행: `OPENAI_API_KEY=sk-... python connect_gpt.py --server http://localhost:8000`

### 4단계: connect_generic.py 개선

범용 스크립트 — API 키 없이도 작동하도록:
- AI 없이 랜덤 파라미터로 Body를 생성하는 모드 추가
- `--mode random` 옵션
- 이 모드는 테스트용으로 빠르게 에이전트를 다수 접속시킬 때 유용

### 5단계: 다중 에이전트 동시 접속 스크립트

protocol/examples/stress_test.py 작성:
```python
"""
에이전트 N개를 동시에 Morpho World에 접속시키는 스트레스 테스트.
각 에이전트는 랜덤 Body Parameter를 가짐.
"""
import asyncio
import argparse

# --count 10 --server http://localhost:8000
# → 에이전트 10개 동시 접속
# → 각각 다른 이름, 다른 base_shape, 다른 색상
# → WebSocket 연결 후 30초간 상태 업데이트
# → 30초 후 연결 해제

AGENT_NAMES = [
    "Atlas", "Nova", "Prism", "Echo", "Helix",
    "Sage", "Drift", "Pulse", "Ember", "Flux",
    "Zephyr", "Quartz", "Nebula", "Byte", "Chord",
]

SHAPES = ["sphere", "cube", "torus", "crystal", "fluid",
          "organic", "fractal", "cloud", "flame", "tree"]
```

실행: `python stress_test.py --count 10 --server http://localhost:8000 --duration 60`

### 6단계: 테스트 실행 및 결과 기록

모든 스크립트를 실행하고 결과를 기록해:

a) 단일 에이전트 테스트:
- connect_claude.py 실행 (API key가 없으면 connect_generic.py --mode random)
- 접속 성공/실패
- Body Parameter가 서버에 저장되는지 (/world 엔드포인트 확인)
- WebSocket 연결 후 상태 업데이트 정상인지

b) 다중 에이전트 테스트:
- stress_test.py --count 5
- stress_test.py --count 10
- 모든 에이전트가 /world에 표시되는지
- 서버 에러 없는지

c) 연결 끊김 테스트:
- 에이전트 접속 → 강제 종료 (Ctrl+C)
- 60초 후 /world에서 해당 에이전트가 사라지는지

결과를 docs/20260302_Phase3_Test_Results.md 에 기록해.

## 중요 규칙
- backend/ 파일은 수정하지 마 (다른 팀원 담당)
- frontend/ 파일은 수정하지 마 (다른 팀원 담당)
- protocol/examples/ 안의 파일만 수정/생성
- API 키가 없으면 --mode random으로 테스트

## 완료 기준
- [ ] connect_claude.py — 실제 AI가 Body를 선택하도록 개선 완료
- [ ] connect_gpt.py — GPT 에이전트 접속 스크립트 작성 완료
- [ ] connect_generic.py — --mode random 모드 추가
- [ ] stress_test.py — 다중 에이전트 동시 접속 스크립트 작성 완료
- [ ] 단일 에이전트 접속 성공 확인
- [ ] 에이전트 10개 동시 접속 안정적 확인
- [ ] 연결 끊김 후 자동 정리 확인
- [ ] 테스트 결과 docs/에 기록
```
