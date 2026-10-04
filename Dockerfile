FROM docker.io/library/python:3.12-slim@sha256:6b1f85a08c199d29d5b6d71ab9c27bd5b3b393492e01216a15758ff69c4be8b8
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml requirements-linux-py312.lock ./
COPY app ./app
RUN pip install --no-cache-dir --require-hashes -r requirements-linux-py312.lock \
    && pip install --no-cache-dir --no-deps --no-build-isolation .
COPY alembic.ini .
COPY migrations ./migrations
COPY scripts/gate738p_contract_upgrade.py ./scripts/gate738p_contract_upgrade.py
COPY scripts/gate738p_crash_writer.py ./scripts/gate738p_crash_writer.py
COPY web ./web
RUN mkdir -p /run/migration-gate && chmod 0755 /run/migration-gate
RUN useradd --create-home --uid 10001 appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
