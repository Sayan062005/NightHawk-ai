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
├── backend/                  # FastAPI 0.115+ asynchronous security service
│   ├── app/
│   │   ├── ai/              # Multi-tier AI engine (NVIDIA NIM + Fallback)
│   │   ├── api/             # REST endpoints (auth, scans, findings, reports)
│   │   ├── core/            # Config, security, database sessions
│   │   ├── models/          # SQLAlchemy async ORM models
│   │   ├── schemas/         # Pydantic v2 validation contracts
│   │   └── services/        # Scan orchestrator, attack graph, report generator
│   └── tests/               # 100% passing test suite (39 tests)
│
├── frontend/                 # React 19 + TypeScript + Vite + Tailwind CSS
│   └── src/
│       ├── components/      # Glassmorphism cyber-aesthetic UI components
│       ├── pages/           # Dashboard, Engagements, Scans, Attack Graph
│       └── services/        # Typed API client with auto JWT refresh
│
├── nighthawk_linux_controller.sh  # Standalone Linux Controller (POSIX Bash)
└── nighthawk_linux_agent.py       # Autonomous Python Linux C2 Agent
```

---

## 🚀 Quick Start

### 1. Standalone Linux Controller (Kali / Ubuntu / Debian)

Take autonomous control of a Linux host with NVIDIA AI:

```bash
# Make executable
chmod +x nighthawk_linux_controller.sh

# Interactive prompt
./nighthawk_linux_controller.sh

# Autonomous mode (-y)
./nighthawk_linux_controller.sh -y "Audit listening ports and check SUID binaries for privesc"
```

### 2. Full Platform Setup

#### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- NVIDIA NIM API Key (get free trial credits at [build.nvidia.com](https://build.nvidia.com))

#### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate
pip install -e .

# Configure environment
cp ../.env.example .env
# Edit .env and supply your NVIDIA_API_KEY

# Run backend API
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

Visit the dashboard at `http://localhost:3000` (or `http://localhost:5173`).

---

## 🛡️ Safety & Responsible Disclosure

NightHawk AI includes strict ethical boundaries:
- Scan execution requires explicit target authorization.
- Destructive commands (`rm -rf /`, `mkfs`, raw block device writes) are blocked by default.
- All actions are recorded to the tamper-evident audit log table.

---

## 🔐 Authentication & Production Security

Browser sessions use short-lived JWT access cookies and rotating opaque refresh cookies. The access and refresh cookies are HttpOnly; the CSRF cookie is readable by the frontend and is echoed in the `X-CSRF-Token` header on state-changing requests. Refresh tokens are stored in the database as SHA-256 hashes, not as plaintext.

### Configure authentication

Generate independent secrets (run twice):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set the generated values in `.env`:

```env
APP_ENV=development
JWT_SECRET_KEY=<first-generated-secret>
ADMIN_BOOTSTRAP_TOKEN=<second-generated-secret>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=14
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
APP_CORS_ORIGINS=["http://localhost:5173"]
```

For the first administrator, open **Create Account** and enter the `ADMIN_BOOTSTRAP_TOKEN` in the optional administrator bootstrap field. The bootstrap is single-use and protected by a database singleton claim. All ordinary registrations become **viewer** accounts. After the first administrator is created, remove `ADMIN_BOOTSTRAP_TOKEN` from the environment and restart the backend. An administrator can promote users through `PATCH /api/v1/auth/users/{user_id}/role` and reset passwords through `POST /api/v1/auth/users/{user_id}/password` (which revokes that user's refresh sessions). A previously issued access cookie can remain valid for at most its 15-minute lifetime.

For production deployments:
- Serve the frontend and API on the same site/hostname (a reverse proxy routing `/api` to FastAPI is recommended); cookies are host-scoped. Do not mix `localhost` and `127.0.0.1` during local development.
- Set `VITE_API_BASE_URL` at frontend build time when the API is not at the default `http://localhost:8000/api/v1`.
- Set `APP_ENV=production`, use HTTPS, and set `AUTH_COOKIE_SECURE=true`.
- Set `APP_CORS_ORIGINS` to the exact frontend origins; do not use wildcard origins with credentials.
- Provide a stable `JWT_SECRET_KEY` of at least 32 bytes and keep it outside source control.
- Use a shared Redis/API-gateway rate limiter when running multiple workers or instances. The included in-process limiter is intended for a single backend process.
- Back up the database. The new refresh-session and admin-bootstrap tables are created at startup by the existing SQLAlchemy table initialization; use Alembic migrations for managed production schema changes.

Passwords are hashed with Argon2id. Existing bcrypt hashes are verified and upgraded to Argon2id after successful login. Legacy bcrypt passwords longer than 72 UTF-8 bytes must be reset because the old bcrypt storage truncated them.

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
