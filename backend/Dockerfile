# NightHawk AI — Backend Dockerfile (Fully Equipped Linux Security Container)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system utilities and Linux security assessment tools.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iproute2 \
    net-tools \
    procps \
    nmap \
    whatweb \
    testssl.sh \
    git \
    unzip \
    jq \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Semgrep static code analysis tool.
RUN pip install --no-cache-dir semgrep

# Install Nuclei (ProjectDiscovery) and OSV-Scanner (Google) on amd64.
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        curl -fsSL https://github.com/projectdiscovery/nuclei/releases/download/v3.3.8/nuclei_3.3.8_linux_amd64.zip -o /tmp/nuclei.zip && \
        unzip -q /tmp/nuclei.zip -d /usr/local/bin nuclei && \
        chmod +x /usr/local/bin/nuclei && rm /tmp/nuclei.zip && \
        curl -fsSL https://github.com/google/osv-scanner/releases/download/v1.9.2/osv-scanner_linux_amd64 -o /usr/local/bin/osv-scanner && \
        chmod +x /usr/local/bin/osv-scanner; \
    fi

# Copy application source before installing the package so setuptools can
# discover the explicitly configured app package.
COPY pyproject.toml ./
COPY app/ ./app/
RUN pip install --no-cache-dir .

COPY tests/ ./tests/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
