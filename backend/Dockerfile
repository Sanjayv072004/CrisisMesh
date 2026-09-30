# Build stage
FROM python:3.10-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final hardened runtime stage
FROM python:3.10-slim AS runner

# Create non-root system group and user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -M appuser

WORKDIR /app

# Copy installed python dependencies from builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code and mock/data assets
COPY --chown=appuser:appgroup backend /app/backend
COPY --chown=appuser:appgroup data /app/data
COPY --chown=appuser:appgroup docs /app/docs

# Switch to unprivileged non-root user
USER appuser

# Healthcheck
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
