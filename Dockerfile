FROM python:3.12-slim

RUN useradd -m appuser && mkdir -p /data && chown appuser /data

WORKDIR /app
COPY pyproject.toml .
COPY app/ app/

RUN pip install --no-cache-dir .

USER appuser
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/api/v1/status')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
