# NightHawk AI 🦅

![NightHawk AI Showcase](nighthawk_showcase.jpg)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19+-61DAFB.svg)](https://react.dev/)
[![NVIDIA NIM](https://img.shields.io/badge/AI-NVIDIA%20NIM%20GLM--5.3-76B900.svg)](https://build.nvidia.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**NightHawk AI** is an autonomous cybersecurity assessment and tactical Linux terminal controller. Built for security researchers and pen-testers, it connects local pentesting workflows with AI reasoning providers and execution safety guardrails.

---

## Core capabilities

- Vulnerability discovery, security header analysis and attack-surface enumeration.
- AI-assisted security assessment with provider fallback.
- Linux security tools and controlled command execution.
- SOC dashboard with findings, engagement tracking and reports.
- Authentication, role checks, rate limits and audit logging.

---

## Architecture

```
NightHawk AI
├── backend/                  # FastAPI asynchronous security service
│   ├── app/
│   │   ├── ai/              # AI provider integration
│   │   ├── api/             # REST endpoints
│   │   ├── core/            # Config, security, database sessions
│   │   ├── models/          # SQLAlchemy async ORM models
│   │   ├── schemas/         # Pydantic API contracts
│   │   └── services/        # Scan orchestration and reporting
│   └── tests/               # Backend regression tests
├── frontend/                 # React + TypeScript + Vite UI
├── deploy/                   # Nginx and Supervisor production configuration
├── Dockerfile.render         # Single-host Render deployment image
├── render.yaml               # Render Blueprint
├── nighthawk_linux_controller.sh
└── nighthawk_linux_agent.py
```

---

## Local setup

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- An NVIDIA NIM API key only when using the NVIDIA provider

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
cp ../.env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm ci
npm run dev
```

Visit the dashboard at the local URL printed by Vite.

---

## Authentication & security

Browser sessions use short-lived JWT access cookies and rotating opaque refresh cookies. The access and refresh cookies are HttpOnly; the CSRF cookie is readable by the frontend and echoed in the `X-CSRF-Token` header on state-changing requests. Refresh tokens are stored in the database as SHA-256 hashes.

Generate independent secrets (run the command twice):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `JWT_SECRET_KEY` and `ADMIN_BOOTSTRAP_TOKEN` in the backend environment. For the first administrator, enter `ADMIN_BOOTSTRAP_TOKEN` in the administrator bootstrap field on the registration page. This bootstrap can only be claimed once. Ordinary registrations receive the **viewer** role. Remove `ADMIN_BOOTSTRAP_TOKEN` from the environment after creating the first administrator.

Passwords use Argon2id. Existing bcrypt hashes are upgraded after a successful login. Legacy bcrypt passwords longer than 72 UTF-8 bytes must be reset because the old bcrypt storage truncated them.

---

## Free deployment on Render

The repository includes a Render Blueprint (`render.yaml`) and a single-host Docker image (`Dockerfile.render`). The frontend and API share one hostname through Nginx, which keeps cookie-based authentication same-origin.

The Blueprint uses the **Free** web-service plan only. It does not create a paid persistent disk or managed database. SQLite is stored in the container's temporary filesystem, so database contents, accounts and findings can be lost when the service restarts, is redeployed, or its free instance is recycled. The free service may also sleep when idle and take time to wake up.

This configuration is intended for a free demo or evaluation environment, not production use with important user data. Keep regular exports/backups of any data you need to retain. No paid service should be enabled without your explicit approval.

Render generates unique JWT, app and first-administrator bootstrap secrets. Retrieve the bootstrap value from the service environment for the first account, then remove it after the administrator is created.

AI runs with the fallback provider by default, so an NVIDIA key is not required for this free deployment. To enable NVIDIA AI later, add a newly rotated key through Render's environment settings—never commit it to Git.

---

## Safety & responsible use

- Scan only targets for which you have explicit authorization.
- Destructive commands are blocked by default.
- Actions are recorded in the audit log.

---

## License

Distributed under the MIT License. See `LICENSE` for details.
