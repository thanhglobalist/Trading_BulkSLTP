# syntax=docker/dockerfile:1.6
#
# sltp-tg-bot — multi-stage build.
# Author: Thanh Nguyen <thanhglobalist@gmail.com>

# ---- builder stage ----------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# OS deps for compiling any C extensions (aiosqlite/uvloop pull pure Python,
# but we keep gcc available for forward-compat).
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install .

# ---- runtime stage ----------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Run as non-root
RUN useradd --system --create-home --uid 1000 sltpbot \
 && mkdir -p /var/lib/sltp-tg-bot /var/log/sltp-tg-bot \
 && chown -R sltpbot:sltpbot /var/lib/sltp-tg-bot /var/log/sltp-tg-bot

COPY --from=builder /opt/venv /opt/venv

WORKDIR /home/sltpbot
USER sltpbot

ENV DB_PATH=/var/lib/sltp-tg-bot/sltp.db \
    LISTEN_HOST=0.0.0.0 \
    LISTEN_PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).status==200 else 1)"

CMD ["python", "-m", "sltp_tg_bot.main"]
