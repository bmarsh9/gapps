# Use Python 3.8 slim image as the builder stage
FROM python:3.8.12-slim-buster AS builder

# Install build-time dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libgirepository1.0-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Use Python 3.8 slim image for the runtime stage
FROM python:3.8.12-slim-buster AS app

# Set the working directory
WORKDIR /app

# Install runtime dependencies as root
RUN apt-get update && apt-get install -y \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and switch to it
RUN useradd -m gapps

# Create the directory for Flask sessions and set permissions
RUN mkdir -p /app/flask_session && chown -R gapps:gapps /app

USER gapps

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local /usr/local/

# Copy the application source code
COPY . .

# Define the command to run the application
CMD ["/bin/bash", "run.sh"]
