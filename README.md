# NightHawk AI 🦅

![NightHawk AI Showcase](nighthawk_showcase.jpg)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19+-61DAFB.svg)](https://react.dev/)
[![NVIDIA NIM](https://img.shields.io/badge/AI-NVIDIA%20NIM%20GLM--5.3-76B900.svg)](https://build.nvidia.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**NightHawk AI** is an autonomous cybersecurity assessment and tactical Linux terminal controller. Built for security researchers and pen-testers, it connects local pentesting workflows with **NVIDIA NIM** reasoning models (`z-ai/glm-5.3` and `z-ai/glm-5.3-flash`) through an automatic fallback system and execution safety guardrails.

---

## ⚡ Core Capabilities

- 🔍 **Autonomous Vulnerability Discovery & Mapping:** Web audits, security header analysis, attack surface enumeration, and attack-graph generation.
- 🧠 **NVIDIA NIM Dual-Model Orchestration:** Primary reasoning powered by `z-ai/glm-5.3` with automatic 3-second fallback to `z-ai/glm-5.3-flash` on timeout or high load.
- 🐧 **Autonomous Linux C2 Agent (`nighthawk_linux_controller.sh`):**
  - Standalone, zero-dependency executable POSIX bash script with embedded Python agent.
  - Interactive REPL and autonomous execution mode (`-y` / `--auto`).
  - Gathers host telemetry (`/etc/os-release`, EUID, installed pentest tools).
  - Safety guardrails blocking destructive commands (`rm -rf /`, raw disk writes, forkbombs).
- 📊 **Security Operations Center (SOC) UI:** Glassmorphism-styled reactive dashboard featuring live logs, finding severity matrices, attack graph visualization, and PDF executive reports.
- 🔒 **Defense-in-Depth:** Mandatory authorization tokens, rate limiters, deterministic fallback providers, and full audit logging.

---

## 🏗️ Architecture

```
NightHawk AI
├── backend/                  # FastAPI asynchronous security service
│   ├── app/
│   │   ├── ai/              # Multi-tier AI engine (NVIDIA NIM + Fallback)
│   │   ├── api/             # REST endpoints (auth, scans, findings, reports)
│   │   ├── core/            # Config, security, database sessions
│   │   ├── models/          # SQLAlchemy async ORM models
│   │   ├── schemas/         # Pydantic v2 validation contracts
│   │   └── services/        # Scan orchestrator, attack graph, report generator
│   └── tests/               # Backend regression tests
│
├── frontend/                 # React + TypeScript + Vite UI
│   └── src/
│       ├── components/      # SOC dashboard components
│       ├── pages/           # Dashboard, Engagements, Scans, Attack Graph
│       └── services/        # Cookie-based API client
│
├── deploy/                   # Nginx and Supervisor production configuration
├── Dockerfile.render         # Single-host Render deployment image
├── render.yaml               # Render Blueprint
├── nighthawk_linux_controller.sh
└── nighthawk_linux_agent.py
```

---

## 🚀 Quick Start

### 1. Standalone Linux Controller (Kali / Ubuntu / Debian)

Take autonomous control of a Linux host with NVIDIA AI:

```bash
chmod +x nighthawk_linux_controller.sh
./nighthawk_linux_controller.sh
./nighthawk_linux_controller.sh -y "Audit listening ports and check SUID binaries for privesc"
```

### 2. Full Platform Setup

#### Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- An NVIDIA NIM API key when using the NVIDIA provider

#### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"

# Copy the example config and set a unique JWT_SECRET_KEY.
cp ../.env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend
```bash
cd frontend
npm ci
npm run dev
```

Visit the dashboard at `http://localhost:3000` (or the Vite URL printed in your terminal).

---

## 🔐 Authentication & Production Security

Browser sessions use short-lived JWT access cookies and rotating opaque refresh cookies. The access and refresh cookies are HttpOnly; the CSRF cookie is readable by the frontend and is echoed in the `X-CSRF-Token` header on state-changing requests. Refresh tokens are stored in the database as SHA-256 hashes, not as plaintext.

Generate independent secrets (run the command twice):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `JWT_SECRET_KEY` and `ADMIN_BOOTSTRAP_TOKEN` in the backend environment. For the first administrator, open **Create Account** and enter `ADMIN_BOOTSTRAP_TOKEN` in the administrator bootstrap field. This bootstrap can only be claimed once. All ordinary registrations receive the **viewer** role. After the first administrator is created, remove `ADMIN_BOOTSTRAP_TOKEN` from the environment and restart the backend.

Passwords use Argon2id. Existing bcrypt hashes are upgraded after a successful login. Legacy bcrypt passwords longer than 72 UTF-8 bytes must be reset because the old bcrypt storage truncated them.

### Production deployment on Render

The repository includes a Render Blueprint (`render.yaml`) and a single-host Docker image (`Dockerfile.render`). The frontend and API share one hostname through Nginx, so cookie-based authentication remains same-origin. SQLite data is stored on a persistent 1 GB disk.

The Blueprint uses a **paid Starter web service plus a persistent disk**. Review the current price and resource plan in the Render plan before approving it. It is configured not to auto-deploy later Git pushes. Render generates unique JWT, app, and first-admin bootstrap secrets; retrieve the bootstrap value from the service environment for the first account, then remove it after the administrator is created.

For Docker Compose deployments, provide `JWT_SECRET_KEY`, `NVIDIA_API_KEY`, and optionally `ADMIN_BOOTSTRAP_TOKEN` in your local environment. Rotate any credentials that have ever been committed to a public repository; deleting them from the current source does not remove them from Git history.

---

## 🛡️ Safety & Responsible Disclosure

- Scan execution requires explicit target authorization.
- Destructive commands (`rm -rf /`, `mkfs`, raw block device writes) are blocked by default.
- All actions are recorded to the audit log table.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
