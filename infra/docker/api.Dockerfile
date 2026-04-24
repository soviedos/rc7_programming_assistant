FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml ./
COPY apps/api/src ./src
COPY apps/api/tests ./tests

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .[dev]

EXPOSE 8000

CMD ["fastapi", "dev", "src/main.py", "--host", "0.0.0.0", "--port", "8000"]
