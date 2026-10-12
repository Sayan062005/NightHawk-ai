# NightHawk AI — Backend Dockerfile (Fully Equipped Linux Security Container)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install system utilities and Linux pentesting packages (nmap, whatweb, testssl, curl, jq)
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

# 2. Install Semgrep static code analysis tool
RUN pip install --no-cache-dir semgrep

# 3. Install Nuclei (ProjectDiscovery vulnerability scanner binary)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        curl -sL https://github.com/projectdiscovery/nuclei/releases/download/v3.3.8/nuclei_3.3.8_linux_amd64.zip -o /tmp/nuclei.zip && \
        unzip -q /tmp/nuclei.zip -d /usr/local/bin nuclei && \
        chmod +x /usr/local/bin/nuclei && \
        rm /tmp/nuclei.zip; \
    fi

# 4. Install OSV-Scanner (Google dependency vulnerability scanner binary)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        curl -sL https://github.com/google/osv-scanner/releases/download/v1.9.2/osv-scanner_linux_amd64 -o /usr/local/bin/osv-scanner && \
        chmod +x /usr/local/bin/osv-scanner; \
    fi

# 5. Copy configuration and install python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# 6. Copy application source code
COPY app/ app/
COPY tests/ tests/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
