FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Shared packages — installed editable first so the app deps are satisfied.
COPY packages/rc7_shared_db /opt/rc7_shared_db
COPY packages/rc7_shared_config /opt/rc7_shared_config
COPY packages/rc7_shared_storage /opt/rc7_shared_storage
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e /opt/rc7_shared_db -e /opt/rc7_shared_config -e /opt/rc7_shared_storage

COPY apps/worker/pyproject.toml ./
COPY apps/worker/src ./src

RUN pip install --no-cache-dir -e ".[dev]"

# Run as non-root for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

CMD ["python", "-m", "src.main"]
