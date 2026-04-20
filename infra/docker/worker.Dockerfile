FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/worker/pyproject.toml ./
COPY apps/worker/src ./src
COPY apps/worker/tests ./tests

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .[dev]

CMD ["python", "-m", "src.main"]
