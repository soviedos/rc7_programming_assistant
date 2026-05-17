FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/worker/pyproject.toml ./
COPY apps/worker/src ./src

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .

# Run as non-root for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

CMD ["python", "-m", "src.main"]
