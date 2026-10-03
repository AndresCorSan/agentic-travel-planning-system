# Build context is the repo root (see docker-compose.yml):
#   context: ., dockerfile: src/backend/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Node.js (weather MCP via npx) + curl/tar (trvl binary download).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates tar \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# trvl CLI (Go binary, single file). Version pinned for reproducibility.
ARG TRVL_VERSION=1.21.6
ARG TARGETARCH
RUN set -eux; \
    arch="${TARGETARCH:-amd64}"; \
    case "$arch" in \
      amd64) _arch=amd64 ;; \
      arm64) _arch=arm64 ;; \
      *) echo "unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/MikkoParkkola/trvl/releases/download/v${TRVL_VERSION}/trvl_${TRVL_VERSION}_linux_${_arch}.tar.gz" \
      | tar xz -C /usr/local/bin trvl; \
    trvl version

# Python deps first (better layer caching). uv sync installs into /app/.venv.
COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv \
    && (uv sync --frozen --no-dev --no-install-project \
        || uv sync --no-dev --no-install-project)
ENV PATH="/app/.venv/bin:$PATH"

COPY src/backend/app ./src/backend/app

WORKDIR /app/src/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
