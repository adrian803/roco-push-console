FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv -q export --frozen --no-dev --format requirements-txt --no-emit-project -o requirements.txt \
    && uv venv /opt/venv \
    && uv pip install --python /opt/venv/bin/python --no-cache -r requirements.txt

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    CONFIG_PATH=/data/config.json \
    APP_MODE=auto \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=19892 \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /data \
    && chown -R app:app /app /data

COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --chown=app:app pyproject.toml README.md main.py ./
COPY --chown=app:app src ./src
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 19892

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -m roco_serverchan_notifier.healthcheck

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "-m", "roco_serverchan_notifier.launcher"]
