FROM python:3.9-slim AS builder

# Install build dependencies
RUN set -euxo pipefail; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        ;

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN set -euxo pipefail; \
    pip install --upgrade \
        pip \
        setuptools \
        wheel; \
    pip install -r requirements.txt

# Final application image
FROM python:3.9-slim AS app

WORKDIR /app

# Install runtime dependencies
RUN set -euxo pipefail; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        libpq5 \
        ;

# Copy pre-installed Python packages from builder
COPY --from=builder /usr/local /usr/local/

COPY . .
CMD ["/app/run.sh"]
