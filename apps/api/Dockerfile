FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv==0.9.4
COPY pyproject.toml uv.lock ./
COPY teapass ./teapass
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f
WORKDIR /app
RUN groupadd --gid 10001 teapass && useradd --uid 10001 --gid 10001 --no-create-home teapass
COPY --from=builder /app/.venv /app/.venv
COPY teapass ./teapass
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "teapass.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "128", "--timeout-keep-alive", "5"]
