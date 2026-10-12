# NightHawk AI — Threat Model

## Assets

| Asset | Sensitivity | Description |
|-------|------------|-------------|
| API Keys (NVIDIA, etc.) | Critical | Must never appear in logs, reports, browser, or prompts |
| Target credentials | Critical | Test account passwords, tokens for authorized testing |
| Finding evidence | High | May contain sensitive data from targets |
| Engagement scope | High | Defines what the system is allowed to touch |
| User sessions | High | JWT tokens, session state |
| Database | High | All findings, evidence, audit trails |
| AI prompts/responses | Medium | May contain target information |

## Threat Actors

1. **Malicious target content** — Websites/APIs that inject prompts or payloads into scanner output
2. **Compromised AI responses** — Model producing scope-escaping or destructive commands
3. **Unauthorized users** — Accessing findings or launching scans without permission
4. **Supply chain attacks** — Compromised dependencies or tool binaries

## Threats and Mitigations

### T1: Prompt Injection via Scanner Output
- **Threat**: Malicious web content contains text designed to manipulate AI agent behavior
- **Mitigation**: All scanner output is treated as untrusted data. AI cannot modify permissions, expand scope, or execute tools directly. Backend validates all actions independently.

### T2: Scope Escape
- **Threat**: AI agent or misconfigured scan targets hosts outside approved scope
- **Mitigation**: Dedicated Scope Enforcement Service validates every outbound request. DNS rebinding protection. SSRF guards. Redirect chain validation. Budget enforcement.

### T3: Arbitrary Command Execution
- **Threat**: AI suggests shell commands that get executed without validation
- **Mitigation**: Execution Broker pattern — no shell interpolation, argument arrays only, tool allowlists, argument validation. Model never has direct shell access.

### T4: Secret Leakage
- **Threat**: API keys, passwords, or tokens appear in logs, reports, or browser
- **Mitigation**: Secret redaction in all output paths. Environment-only credential storage. Server-side-only secret access. Log sanitization.

### T5: Unauthorized Access
- **Threat**: Users access findings or trigger scans without authorization
- **Mitigation**: JWT authentication, role-based access control, per-engagement authorization, audit logging.

### T6: Denial of Service via Unbounded Execution
- **Threat**: Assessment loops indefinitely consuming resources
- **Mitigation**: Configurable budgets (time, requests, tokens, iterations), per-task timeouts, dead-letter queues, emergency stop.

### T7: False Evidence Fabrication
- **Threat**: AI generates fake vulnerability findings or evidence
- **Mitigation**: Verification agent independently checks evidence. Confidence scoring requires reproducible proof. Findings without evidence are marked as candidates only.

### T8: DNS Rebinding
- **Threat**: Target DNS changes to internal IP after initial scope check
- **Mitigation**: DNS resolution cached per-request. Re-validated before connection. Internal/loopback/link-local blocked unless lab profile.

### T9: SSRF via Redirects
- **Threat**: Approved target redirects to internal resources
- **Mitigation**: Redirect destinations validated against scope. Maximum redirect count. Internal addresses blocked.

### T10: Supply Chain
- **Threat**: Malicious updates to dependencies or security tools
- **Mitigation**: Dependency pinning, SBOM generation, hash verification where feasible, minimal privilege for tool execution.

## Trust Boundaries

```
[Browser] ──HTTPS──> [FastAPI + Auth] ──Validated──> [Agent Layer]
                                                          │
                                                    [Scope Service]
                                                          │
                                                   [Execution Broker]
                                                          │
                                                    [External Tools]
                                                          │
                                                   [Target Systems]
```

Every arrow crossing a trust boundary has validation, authentication, or sanitization.
