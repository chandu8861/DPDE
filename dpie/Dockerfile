FROM python:3.11-slim

LABEL maintainer="DPIE Team"
LABEL description="DPIE - DarkPattern Intelligence Engine"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DPIE_ENVIRONMENT=production \
    DPIE_API_PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration and project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY SUMMARY.md ./

# Install package
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir .

# Create non-root user
RUN useradd -m -u 1000 dpieuser && \
    chown -R dpieuser:dpieuser /app
USER dpieuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["dpie", "serve", "--host", "0.0.0.0", "--port", "8000"]

