FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml .
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic-settings sqlalchemy asyncpg aiosqlite redis PyJWT alembic httpx pytest pytest-asyncio ruff mypy pgvector reportlab
COPY alembic.ini .
COPY migrations ./migrations
COPY app ./app
COPY web ./web
RUN useradd --create-home --uid 10001 appuser
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
