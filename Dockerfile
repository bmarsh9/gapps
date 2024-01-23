# Using Ubuntu 20.04 as the base image
FROM ubuntu:20.04 AS builder

# Set noninteractive environment to avoid prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies for the build stage
RUN apt-get update && apt-get install -y libpq-dev python3-pip gcc \
    && pip install --upgrade pip setuptools wheel

# Copy only the requirements.txt to install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Start the second stage for the actual application
FROM ubuntu:20.04 AS app

# Set noninteractive environment
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory inside the container
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y libpq5 python3.8 weasyprint=51-2 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local /usr/local/

# Copy the application source code to the container
COPY . .

# Define the command to run the application
CMD ["/bin/bash", "run.sh"]
