FROM ubuntu:24.04 AS builder
ENV DEBIAN_FRONTEND=noninteractive

# Builder stage dependencies aren't needed by the app at runtime
RUN apt-get update && apt-get install -y \
    libpq-dev \
    python3-pip \
    gcc
COPY requirements.txt .
RUN pip install --break-system-packages -r requirements.txt

FROM ubuntu:24.04 AS app
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app
RUN apt-get update && apt-get install -y libpq5 python3.12 weasyprint \
  && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local /usr/local/
COPY . .
CMD ["/bin/bash", "run.sh"]
