FROM python:3.8-slim-buster AS builder
# Builder stage dependencies aren't needed by the app at runtime
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

FROM python:3.8-slim-buster AS app
WORKDIR /app
RUN apt-get update && apt-get install -y libpq5 \
  && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local /usr/local/
COPY . .
CMD ["/bin/bash", "run.sh"]
