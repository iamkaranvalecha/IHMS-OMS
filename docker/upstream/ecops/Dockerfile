# syntax=docker/dockerfile:1.4
# Build EC-OPS from a sibling checkout (build context = EC-OPS repo root).
# Entrypoint script lives in the oms-docker additional build context (see compose.bundle.yml).

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts

RUN uv sync --no-dev

COPY --from=oms-docker docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PORT=8002 \
    JWT_SECRET_KEY=dev-docker-secret-change-me \
    JWT_ALGORITHM=HS256 \
    ACCESS_TOKEN_EXPIRE_MINUTES=1440 \
    LOG_LEVEL=INFO

EXPOSE 8002

HEALTHCHECK --interval=10s --timeout=5s --retries=12 --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8002/health')"

ENTRYPOINT ["/docker-entrypoint.sh"]
