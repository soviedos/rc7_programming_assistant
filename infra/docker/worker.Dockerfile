FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/worker/pyproject.toml ./
COPY apps/worker/src ./src

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .

CMD ["python", "-m", "src.main"]
