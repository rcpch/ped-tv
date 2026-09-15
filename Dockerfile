FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Keep the virtualenv outside /app so volume mounts don't hide installed packages
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync

COPY . .

# NHS UK frontend assets are gitignored (s/bootstrap downloads them for dev),
# so fetch them here too — image builds must be self-contained.
RUN mkdir -p static/nhsuk \
    && curl -sSf -o static/nhsuk/nhsuk.min.css "https://cdn.jsdelivr.net/npm/nhsuk-frontend/dist/nhsuk.min.css" \
    && curl -sSf -o static/nhsuk/nhsuk.min.js "https://cdn.jsdelivr.net/npm/nhsuk-frontend/dist/nhsuk.min.js"

# Collect static files so WhiteNoise can serve them with hashed filenames.
# Only a dummy SECRET_KEY is needed: collectstatic uses the staticfiles
# storage backend and touches neither the database nor media storage.
RUN SECRET_KEY=build-time-only python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
