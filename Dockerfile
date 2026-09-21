FROM node:24-bookworm-slim AS web
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.13
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY backend/ backend/
RUN uv sync --frozen --no-dev
COPY alembic.ini ./
COPY scripts/ scripts/
COPY config/ config/
COPY --from=web /src/frontend/dist frontend/dist
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "damsafe.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
