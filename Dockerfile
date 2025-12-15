# Discord A/B/C Todo Bot Dockerfile
# Multi-stage build for a minimal production image

# =============================================================================
# Stage 1: Build stage
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and install the package
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# =============================================================================
# Stage 2: Production stage
# =============================================================================
FROM python:3.11-slim as production

# Create non-root user for security
RUN groupadd -r todobot && useradd -r -g todobot todobot

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create data directory for SQLite database
RUN mkdir -p /app/data && chown -R todobot:todobot /app/data

# Copy source code
COPY --from=builder /app/src /app/src

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/app/data/tasks.db \
    LOG_LEVEL=INFO

# Switch to non-root user
USER todobot

# Health check - verify Python and package are working
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from todo_bot import TodoBot; print('OK')" || exit 1

# Run the bot
CMD ["python", "-m", "todo_bot.main"]
