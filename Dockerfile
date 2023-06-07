# Need to clean this up - had to move to ubuntu:20.04 because
# weasyprint would not properly show SVG icons under 
# python:3.8-slim-buster. Using ubuntu increases the image size
# by 250 MB which is terrible. Need to get weasyprint working
# on python image

#FROM python:3.8-slim-buster AS builder
FROM ubuntu:20.04 AS builder
ENV DEBIAN_FRONTEND=noninteractive

# Builder stage dependencies aren't needed by the app at runtime
RUN apt-get update && apt-get install -y \
    libpq-dev \
    python3-pip \
    gcc
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

#FROM python:3.8-slim-buster AS app
FROM ubuntu:20.04 AS app
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app
#RUN apt-get update && apt-get install -y libpq5 python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libpangocairo-1.0-0 \
RUN apt-get update && apt-get install -y libpq5 python3.8 weasyprint=51-2 \
  && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local /usr/local/
COPY . .
CMD ["/bin/bash", "run.sh"]
