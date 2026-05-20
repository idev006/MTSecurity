# Stage 1: Build — install Python dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools needed for some native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only the dependency manifest first for better cache reuse
COPY pyproject.toml ./

# Install all runtime dependencies into a prefix we can copy later
RUN pip install --upgrade pip && \
    pip install --prefix=/install \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.30" \
    "python-multipart>=0.0.9" \
    "pydantic>=2.7" \
    "pydantic-settings>=2.3" \
    "sqlalchemy>=2.0" \
    "aiosqlite>=0.20" \
    "alembic>=1.13" \
    "asyncpg>=0.29" \
    "pyjwt>=2.8" \
    "bcrypt>=4.1" \
    "cryptography>=42" \
    "httpx>=0.27" \
    "cachetools>=5.3" \
    "opencv-python-headless>=4.9" \
    "line-bot-sdk>=3.10" \
    "paho-mqtt>=2.0" \
    "jinja2>=3.1" \
    "python-dotenv>=1.0" \
    "psutil>=5.9" \
    "slowapi>=0.1.9" \
    "anyio>=4.4" \
    "openvino>=2024.0" \
    "redis>=5.0" \
    "limits[redis]>=3.7"


# Stage 2: Lean runtime image
FROM python:3.12-slim AS runtime

# Install system libraries required at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local

WORKDIR /app

# Create a non-root user for security
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/bash --create-home appuser

# Copy application source
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["python", "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
