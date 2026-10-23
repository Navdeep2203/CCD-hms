#Use the floating Python 3.12 slim tag to receive updated patch releases. 
#It's less reproducible than a pinned patch or a digest.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system --gid 1000 appgroup && \
    useradd --system \
        --uid 1000 \
        --gid appgroup \
        --no-create-home \
        --shell /usr/sbin/nologin \
        appuser

WORKDIR /app
COPY backend/requirements.txt requirements.txt

RUN python -m pip install --no-cache-dir -r requirements.txt

FROM base AS prod

COPY --chown=appuser:appgroup backend/app /app/app
COPY --chown=appuser:appgroup database/migrations /app/database/migrations
COPY --chown=appuser:appgroup --chmod=755 backend/entrypoint.sh /app/entrypoint.sh

ENV MIGRATIONS_DIR=/app/database/migrations
ENV PORT=8000

USER appuser:appgroup

#Use the ready endpoint to ensure database is also connected for proper functioning of backend
HEALTHCHECK --interval=10s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; \
    urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health/ready', timeout=5)"

ENTRYPOINT [ "/app/entrypoint.sh" ]