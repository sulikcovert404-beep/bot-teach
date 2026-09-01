FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml .
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic-settings sqlalchemy asyncpg aiosqlite PyJWT alembic httpx pytest pytest-asyncio ruff mypy
COPY app ./app
COPY web ./web
COPY tests ./tests
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
