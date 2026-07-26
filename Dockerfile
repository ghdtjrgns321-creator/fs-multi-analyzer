# 실행 전용 이미지 — 대시보드를 띄우는 것이 목적이다(테스트·lint는 로컬 uv).
# 데이터(data/)·설정(config/)·시크릿(.env)은 굽지 않고 호스트에서 주입한다.
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# 의존성 레이어를 소스와 분리 — 코드만 고치면 재설치가 일어나지 않는다.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project \
    --group core --group agent --group dashboard

COPY . .

EXPOSE 8501

# Streamlit 자체 헬스 엔드포인트 — 컨테이너가 "떴는지"가 아니라 "응답하는지"를 본다.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "dashboard/app.py", \
    "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
