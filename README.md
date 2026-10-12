# NightHawk AI 🛡️🤖

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19+-61DAFB.svg)](https://react.dev/)
[![NVIDIA NIM](https://img.shields.io/badge/AI-NVIDIA%20NIM%20GLM--5.3-76B900.svg)](https://build.nvidia.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**NightHawk AI** is an advanced, autonomous AI-powered security assessment, red-team penetration testing, blue-team defensive telemetry investigation, and Linux command-and-control platform.

Engineered for security researchers, penetration testers, and DevSecOps engineers, NightHawk AI pairs local security orchestration with **NVIDIA NIM** reasoning models (`z-ai/glm-5.3` and `z-ai/glm-5.3-flash`) with robust latency fallback and execution safety guardrails.

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

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
