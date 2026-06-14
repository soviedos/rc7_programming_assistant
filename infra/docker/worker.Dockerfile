FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Shared ORM package — installed editable first so the app dep is satisfied.
COPY packages/rc7_shared_db /opt/rc7_shared_db
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e /opt/rc7_shared_db

COPY apps/worker/pyproject.toml ./
COPY apps/worker/src ./src

RUN pip install --no-cache-dir -e ".[dev]"

# Run as non-root for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

CMD ["python", "-m", "src.main"]
