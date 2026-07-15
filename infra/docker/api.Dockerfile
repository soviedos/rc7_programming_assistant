FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# Shared packages — installed editable first so the app deps are satisfied.
COPY packages/rc7_shared_db /opt/rc7_shared_db
COPY packages/rc7_shared_config /opt/rc7_shared_config
COPY packages/rc7_shared_storage /opt/rc7_shared_storage
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e /opt/rc7_shared_db -e /opt/rc7_shared_config -e /opt/rc7_shared_storage

COPY apps/api/pyproject.toml ./
COPY apps/api/src ./src

RUN pip install --no-cache-dir -e ".[dev]"

# Run as non-root for security
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]
