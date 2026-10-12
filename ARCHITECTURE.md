# NightHawk AI — Architecture

## Overview

NightHawk AI is a modular, AI-augmented security assessment platform implementing a multi-agent architecture for continuous vulnerability research, red team/blue team operations, and remediation tracking.

**Core Workflow:** Discover → Map → Test → Analyze → Verify → Correlate → Report → Remediate → Retest

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/Vite)                     │
│  Dashboard │ Engagement │ Findings │ Attack Graph │ Blue Team    │
│  WebSocket/SSE Live Updates │ Theme: Dark/Light                  │
└──────────────────────────┬───────────────────────────────────────┘
                           │ HTTPS / WSS
┌──────────────────────────▼───────────────────────────────────────┐
│                      API GATEWAY (FastAPI)                        │
│  Auth │ RBAC │ Rate Limiting │ Input Validation │ Audit Log      │
├──────────────────────────────────────────────────────────────────┤
│                    SCOPE ENFORCEMENT SERVICE                     │
│  Host Validation │ SSRF Prevention │ DNS Rebind Guard            │
│  Budget Tracking │ Request Proxy │ Redirect Following            │
├──────────────────────────────────────────────────────────────────┤
│                     EXECUTION BROKER                             │
│  Sandboxed Subprocess │ Argument Validation │ Output Sanitize    │
│  Timeout/Size Limits │ No Shell Interpolation                    │
├──────────────────────────────────────────────────────────────────┤
│                      AGENT LAYER                                 │
│  ┌────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │Orchestrator│ │  Recon   │ │ Red Team │ │   Blue Team      │  │
│  └────────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌────────────┐ ┌──────────┐ ┌──────────────────────────────┐   │
│  │Verification│ │ Research │ │       Reporting              │   │
│  └────────────┘ └──────────┘ └──────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│                    AI PROVIDER LAYER                              │
│  NVIDIA NIM │ OpenAI-compat │ Local Model │ Rule Fallback        │
│  Schema Validation │ Token Accounting │ Mock for Tests           │
├──────────────────────────────────────────────────────────────────┤
│                   TOOL ADAPTERS                                   │
│  Nmap │ WhatWeb │ testssl.sh │ ZAP │ Nuclei │ Semgrep           │
│  OSV-Scanner │ Playwright │ curl │ Native Checks                │
├──────────────────────────────────────────────────────────────────┤
│                   DATA LAYER                                      │
│  SQLite/PostgreSQL │ Alembic Migrations │ Redis Task Queue       │
│  Evidence Store │ Attack Graph │ Audit Events                    │
└──────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
nighthawk/
├── backend/
│   ├── alembic/                  # Database migrations
│   ├── app/
│   │   ├── api/                  # FastAPI routes
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── engagements.py
│   │   │   │   ├── findings.py
│   │   │   │   ├── scans.py
│   │   │   │   ├── assets.py
│   │   │   │   ├── reports.py
│   │   │   │   ├── blueteam.py
│   │   │   │   ├── tools.py
│   │   │   │   └── system.py
│   │   │   └── deps.py
│   │   ├── agents/               # AI Agents
│   │   │   ├── base.py
│   │   │   ├── orchestrator.py
│   │   │   ├── recon.py
│   │   │   ├── redteam.py
│   │   │   ├── blueteam.py
│   │   │   ├── verification.py
│   │   │   ├── research.py
│   │   │   └── reporting.py
│   │   ├── core/                 # Core services
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── scope.py
│   │   │   ├── execution.py
│   │   │   └── logging.py
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/             # Business logic
│   │   ├── tools/                # Tool adapters
│   │   ├── ai/                   # AI provider layer
│   │   └── main.py
│   ├── tests/
│   ├── alembic.ini
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── docker/
├── docs/
├── .env.example
├── docker-compose.yml
├── README.md
└── LICENSE
```

## Key Design Decisions

### 1. Scope Enforcement is Backend-Only
The scope enforcement service is a server-side component that validates every outbound request. AI agents cannot bypass it. This is the primary security boundary.

### 2. Execution Broker Pattern
All external tool invocations go through a centralized execution broker that:
- Uses argument arrays (no shell interpolation)
- Validates tool + arguments against allowlists
- Enforces timeouts and output size limits
- Runs in isolated subprocesses

### 3. AI is Advisory, Not Authoritative
AI model output is treated as suggestions. The backend independently validates:
- Task permissions against scope
- Tool arguments against allowlists
- Finding claims against evidence

### 4. Typed Agent Communication
Agents communicate via structured Pydantic messages, not free-form text. Task contracts define inputs, outputs, and side effects.

### 5. Database-First State
All state is persisted to the database. Assessments can be paused, resumed, and recovered from crashes. No ephemeral-only state for critical workflows.

## Data Flow

1. User creates an engagement with scope definition
2. Orchestrator builds initial task graph
3. Tasks are dispatched to specialist agents
4. Agents propose tool executions → Execution Broker validates → Scope Service checks
5. Tool outputs are normalized into findings
6. Verification agent re-assesses findings
7. Evidence is stored with full provenance
8. Reports are generated from verified findings
9. Remediation items are tracked
10. Regression tests validate fixes

## Security Boundaries

| Boundary | Mechanism |
|----------|-----------|
| AI → Tools | Execution Broker validates all arguments |
| Tools → Network | Scope Enforcement Service blocks prohibited targets |
| Frontend → Backend | JWT auth, RBAC, input validation |
| Scanner Output → AI | Treated as untrusted input, sanitized |
| Secrets → Logs/Reports | Redaction service strips sensitive data |
| AI Prompts → Actions | Backend independently validates all AI suggestions |
