# 🟡 Claude Code 2 — 프론트엔드 + 배포 설정 지시문

아래 내용을 Claude Code 터미널에 복사해서 붙여넣으세요.
**⚠️ Claude Code 1이 서버를 먼저 올려야 프론트엔드 테스트 가능. 배포 설정은 바로 시작 가능.**

---

```
너는 "Morpho World" 프로젝트의 프론트엔드 + 배포 설정 담당이야.
프로젝트 위치: 04_morpho-world/

## 프로젝트 이해
Morpho World는 AI 에이전트들이 스스로 3D 형태를 선택하고 가상 세계에 존재하는 프로젝트야.
사람은 브라우저에서 관찰만 해. Three.js로 3D 렌더링.

## 현재 상태
- frontend/observe.html — Observer 인터페이스 완성
- frontend/js/body-generator.js — 파라미터 → 3D 형태 변환
- frontend/js/agent-animator.js — 에이전트 움직임/상태 애니메이션
- frontend/js/observer-controls.js — 카메라 조작
- backend/ — 다른 팀원(Code 1)이 담당 중, 수정하지 마

## 네 할 일

### Part A: 배포 설정 (서버 없어도 바로 시작 가능)

#### A-1. Dockerfile 작성
04_morpho-world/ 루트에 Dockerfile 생성:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### A-2. Railway용 Procfile 작성
04_morpho-world/ 루트에:
```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

#### A-3. .env.example 작성
04_morpho-world/ 루트에:
```
# Morpho World Environment Variables
# Copy this to .env and fill in values

# Server
HOST=0.0.0.0
PORT=8000

# Optional: Database (default: SQLite)
# DATABASE_URL=sqlite:///data/morpho.db
```

#### A-4. .gitignore 정리
04_morpho-world/ 루트에 .gitignore 생성 또는 수정:
```
__pycache__/
*.pyc
*.pyo
.env
data/*.db
*.db
.DS_Store
node_modules/
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
```

#### A-5. LICENSE 파일 (MIT)
04_morpho-world/ 루트에 MIT 라이센스 파일 생성.
저작자: Ju Hae Lee, 연도: 2026

---

### Part B: 프론트엔드 테스트 (Code 1이 서버 올린 후)

서버가 http://localhost:8000 에서 실행 중일 때:

#### B-1. 기본 렌더링 확인
- 브라우저에서 http://localhost:8000/observe 열기
- Three.js 씬이 렌더링되는지 확인:
  - 어두운 배경 (0x050510)
  - 바닥 그리드
  - 별 파티클
  - 안개 효과
  - 조명 (앰비언트 + 포인트 라이트 2개)
- 에러가 있으면 콘솔(F12)에서 확인 후 수정

#### B-2. body-generator.js 테스트
- 더미 데이터로 10가지 base_shape 모두 렌더링 테스트
- 콘솔에서 직접 테스트 가능:
  ```javascript
  // 콘솔에서 테스트
  const shapes = ['sphere','cube','torus','crystal','fluid','organic','fractal','cloud','flame','tree'];
  shapes.forEach((s, i) => {
      const group = MorphoBodyGenerator.generate({
          base_shape: s,
          color_primary: `hsl(${i*36}, 70%, 60%)`,
          complexity: 0.7,
          scale: 1.0,
          emissive_intensity: 0.5,
          particle_type: 'glow',
          aura_radius: 0.8,
      }, THREE);
      group.position.set(i * 3 - 15, 1, 0);
      scene.add(group);
  });
  ```
- 각 형태가 시각적으로 구분되는지 확인
- 극단값 테스트 (scale: 0.3, scale: 3.0 등)

#### B-3. observer-controls.js 테스트
- 마우스 드래그 → 카메라 회전
- 스크롤 → 줌 인/아웃
- WASD → 카메라 이동 (있다면)
- 더블클릭 → 에이전트 근처로 이동 (있다면)
- 동작이 부드러운지 (jitter 없는지)

#### B-4. 에이전트 hover/tooltip 확인
- 에이전트 위에 마우스 올리면 tooltip 표시
- tooltip에 이름, 모델, 상태, 형태 설명, self_reflection 표시
- tooltip이 화면 밖으로 넘어가지 않는지

#### B-5. 성능 확인
- 에이전트 10개일 때 30fps 이상 유지되는지
- 콘솔에서 `renderer.info` 확인
- 너무 느리면 최적화 포인트 기록

### 수정이 필요하면
- observe.html, js/ 파일들만 수정
- 수정 시 주석으로 변경 사항 기록
- backend/ 파일은 절대 수정하지 마

## 완료 기준
- [ ] Dockerfile 작성 완료
- [ ] Procfile 작성 완료
- [ ] .env.example 작성 완료
- [ ] .gitignore 정리 완료
- [ ] LICENSE (MIT) 생성 완료
- [ ] observe.html 기본 렌더링 정상 (Part B는 서버 올라간 후)
- [ ] 10가지 base_shape 모두 렌더링 확인
- [ ] 카메라 조작 부드럽게 작동
```
