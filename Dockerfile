FROM python:3.11-slim

LABEL org.opencontainers.image.title="Find My Timeline"
LABEL org.opencontainers.image.description="Store and display historical Apple Find My device locations"
LABEL org.opencontainers.image.source="https://github.com/heckpiet/find-my-timeline-unraid"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    WEB_HOST=0.0.0.0 \
    WEB_PORT=5000 \
    DATABASE_PATH=/app/data/locations.db \
    AUTH_SESSION_LIFETIME_DAYS=90 \
    WEB_AUTH_ENABLED=false

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

RUN pip install --no-cache-dir -e .

VOLUME ["/root/.find-my-timeline", "/app/data"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/stats', timeout=3)" || exit 1

CMD ["find-my-timeline", "start"]
