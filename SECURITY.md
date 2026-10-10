# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in SentinelWeb AI, please report it responsibly:

1. **Do NOT** open a public GitHub issue for security vulnerabilities.
2. Email: security@sentinelweb.example (placeholder — update before public release)
3. Include: description, reproduction steps, impact assessment, and suggested fix if available.
4. We will acknowledge receipt within 48 hours and provide a timeline for resolution.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Current development |

## Security Design Principles

1. **Defense in depth**: Multiple independent security boundaries
2. **Least privilege**: Tools run with minimal permissions
3. **Fail secure**: Missing tools, failed checks, and invalid input produce safe errors
4. **No implicit trust**: AI output, scanner output, and user input are all validated
5. **Audit everything**: All security-relevant actions are logged with timestamps and actors

## Credential Handling

- All secrets stored in `.env` files (never committed)
- `.env.example` contains placeholders only
- Server-side only access to API keys
- Automatic redaction from logs and reports
- No secrets in error messages or stack traces

## Responsible Use

This tool is designed for **authorized security testing only**. Users must:
- Have written authorization for all targets
- Respect scope boundaries configured in engagements
- Follow applicable laws and regulations
- Report vulnerabilities responsibly to affected parties
- Never use findings for unauthorized access or harm
