# NightHawk AI — Backend Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Linux networking and reconnaissance tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iproute2 \
    net-tools \
    procps \
    nmap \
    jq \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration and install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application source code
COPY app/ app/
COPY tests/ tests/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
