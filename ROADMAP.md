# SentinelWeb AI — Roadmap

## Phase 1: Foundation ← CURRENT
- [x] Repository inspection and environment analysis
- [x] Architecture documentation
- [x] Threat model
- [ ] Application skeleton (FastAPI + React/Vite)
- [ ] Database models and migrations
- [ ] Authentication and session management
- [ ] Scope Enforcement Service
- [ ] Audit logging
- [ ] Configuration management

## Phase 2: Tool Infrastructure
- [ ] Tool inventory and detection
- [ ] Execution Broker (sandboxed subprocess)
- [ ] Scanner adapters (Nmap, Nuclei, etc.)
- [ ] Task queue with persistence
- [ ] WebSocket/SSE live progress

## Phase 3: Finding Engine
- [ ] Finding normalization schema
- [ ] Evidence storage with redaction
- [ ] Verification workflow
- [ ] Report generation (HTML, JSON, Markdown, SARIF)

## Phase 4: AI Integration
- [ ] NVIDIA NIM provider
- [ ] OpenAI-compatible adapter
- [ ] Mock provider for tests
- [ ] Rule-based fallback
- [ ] Multi-agent orchestration
- [ ] Autonomous assessment planning
- [ ] Persistent checkpoints and budgets

## Phase 5: Red Team
- [ ] Operating profiles (Passive, Active, Lab)
- [ ] Security check catalog
- [ ] Attack-path graph
- [ ] Lab environment with OWASP targets

## Phase 6: Blue Team
- [ ] Log ingestion
- [ ] Detection rules
- [ ] Incident timeline
- [ ] Purple Team regression testing
- [ ] Remediation workflow

## Phase 7: Polish
- [ ] Full dashboard UI
- [ ] Export formats
- [ ] Benchmarking
- [ ] CI/CD pipeline
- [ ] Documentation
- [ ] Packaging and deployment
