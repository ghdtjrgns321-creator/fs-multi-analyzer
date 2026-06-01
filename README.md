# Disclosure Review Agent

멀티에이전트 교차검증 기반 **공시 재무제표·주석 변화 리뷰 도구**.

OpenDART XBRL 재무제표·주석을 수집해 BS-IS-CF 숫자 흐름, 주석 근거, 전기 대비 공시 변화를
교차검증하여, 감사인이 검토할 재무제표 리스크 후보를 제안하는 Human-in-the-Loop 도구다.
부정을 확정하지 않는다.

## 문서

문서는 보는 주체에 따라 나뉜다 — 안내: [docs/README.md](docs/README.md)

- 🤖 AI 작업 진입점: [docs/agent/STATE.md](docs/agent/STATE.md) (현재 상태) · [docs/agent/OVERVIEW.md](docs/agent/OVERVIEW.md) (전체 흐름)
- 설계 단일 출처: [docs/agent/PLAN.md](docs/agent/PLAN.md)
- 결정 로그: [docs/agent/DECISION.md](docs/agent/DECISION.md) · 자산 정리: [docs/agent/SETUP.md](docs/agent/SETUP.md)
- 👤 사람용 문제 해결 기록: [docs/user/TROUBLESHOOT.md](docs/user/TROUBLESHOOT.md)
- 작업 규약: [AGENTS.md](AGENTS.md) (Codex/공통) · [CLAUDE.md](CLAUDE.md) (Claude)

## 빠른 시작

```bash
uv sync --group core --group agent --group dashboard --group dev
cp .env.example .env   # API 키 입력 (DART_API_KEY 등)
uv run pytest tests -q
uv run streamlit run dashboard/app.py
```

## 구조

```
src/
  collect/        L0  OpenDART 수집
  normalize/      L1  XBRL → canonical + mapping confidence
  notes/          L1.5 주석 인덱서 (섹션 분류·note diff)
  signals/        L2  신호엔진 (materiality·관계사슬·QoE·변화)
  analysis_tools/     tool DSL (LLM 호출 함수)
  agents/         L3  역할 에이전트 5개 (PydanticAI)
  orchestrate/        순수 Python async 파이프라인
  report/         L4  Finding 종합
  schemas/            Finding 스키마
  db/                 DuckDB 격리
config/playbooks/   회계 항등식·관계사슬·watchlist (지식은 데이터)
dashboard/          L5  Streamlit
```
