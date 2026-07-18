# backend/Dockerfile
# Version: 1.2.0 (2026-07-18)
#
# Changelog:
#   1.2.0 - Add ENVIRONMENT (default DEVELOPMENT), surfaced in GET
#           /api/health alongside version. Unlike APP_VERSION, this is meant
#           to be overridden without a rebuild (`docker run -e
#           ENVIRONMENT=PRODUCTION` or a compose environment: entry) — a
#           plain container ENV read live by Python at request time needs no
#           bake-time/start-time split the way the frontend's equivalent
#           does (see frontend/Dockerfile).
#   1.1.0 - Bake BUILD_VERSION/BUILD_SHA/BUILD_DATE: OCI image labels plus
#           APP_VERSION exposed at runtime (surfaced in GET /api/health), so a
#           running container's version is inspectable without a registry tag.
#   1.0.0 - Baseline: single-stage image, Poetry main deps only.

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-interaction

COPY main.py ./
COPY core/ core/
COPY api/ api/

ARG BUILD_VERSION=0.0.0-dev.0
ARG BUILD_SHA=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.version="${BUILD_VERSION}" \
      org.opencontainers.image.revision="${BUILD_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.title="pdns-admin-lite-backend" \
      org.opencontainers.image.source="https://github.com/Supaahiro/pdns-admin-lite"

ENV APP_VERSION=${BUILD_VERSION}

# Default for local `docker run`/one-off use; docker-compose.yml and anyone
# else running this image can override without a rebuild.
ENV ENVIRONMENT=DEVELOPMENT

RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
