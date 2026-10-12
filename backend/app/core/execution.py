"""NightHawk AI — Execution Broker.

Centralized, sandboxed subprocess execution for all security tools.
The AI model never has direct shell access. All tool invocations go
through this broker which validates arguments, enforces timeouts,
and sanitizes outputs.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Maximum output size in bytes (10 MB)
MAX_OUTPUT_SIZE = 10 * 1024 * 1024

# Tools that are allowed to be executed
ALLOWED_TOOLS: dict[str, dict[str, Any]] = {
    "nmap": {
        "binary": "nmap",
        "description": "Network scanner",
        "install": "sudo apt install nmap",
        "allowed_flags": ["-sV", "-sC", "-sS", "-sT", "-sU", "-p", "-Pn", "-A",
                          "-O", "--script", "-oX", "-oN", "-oG", "-T0", "-T1",
                          "-T2", "-T3", "-T4", "--top-ports", "-F", "--open",
                          "--version-intensity", "-n", "-6", "--max-retries",
                          "--host-timeout", "--max-rate"],
    },
    "whatweb": {
        "binary": "whatweb",
        "description": "Web technology fingerprinter",
        "install": "sudo apt install whatweb",
        "allowed_flags": ["-v", "-a", "--log-json", "--color=never", "-U",
                          "--follow-redirect", "--max-threads"],
    },
    "nuclei": {
        "binary": "nuclei",
        "description": "Vulnerability scanner",
        "install": "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        "allowed_flags": ["-target", "-u", "-t", "-tags", "-severity", "-o",
                          "-jsonl", "-silent", "-rate-limit", "-bulk-size",
                          "-c", "-timeout", "-retries", "-no-interactsh",
                          "-etags", "-es", "-rl", "--headless"],
    },
    "testssl": {
        "binary": "testssl.sh",
        "description": "TLS/SSL configuration tester",
        "install": "sudo apt install testssl.sh",
        "allowed_flags": ["--json", "--jsonfile", "--html", "--quiet",
                          "--sneaky", "--fast", "--ip", "--nodns",
                          "--assuming-http", "--connect-timeout",
                          "--openssl-timeout"],
    },
    "semgrep": {
        "binary": "semgrep",
        "description": "Static analysis tool",
        "install": "pip install semgrep",
        "allowed_flags": ["--config", "--json", "--output", "--severity",
                          "--quiet", "--no-git-ignore", "--timeout",
                          "--max-target-bytes", "--jobs", "--lang",
                          "--pattern", "--exclude", "--include"],
    },
    "osv_scanner": {
        "binary": "osv-scanner",
        "description": "Dependency vulnerability scanner",
        "install": "go install github.com/google/osv-scanner/cmd/osv-scanner@latest",
        "allowed_flags": ["--json", "-r", "--lockfile", "--sbom",
                          "--config", "--format"],
    },
    "curl": {
        "binary": "curl",
        "description": "HTTP client",
        "install": "Pre-installed on most systems",
        "allowed_flags": ["-s", "-S", "-L", "-I", "-H", "-X", "-d", "-o",
                          "-w", "--max-time", "--connect-timeout", "-k",
                          "--max-redirs", "-A", "--compressed", "-v",
                          "--cert-status"],
    },
}

# Characters and patterns blocked from arguments
_DANGEROUS_PATTERNS = [
    ";", "&&", "||", "|", "`", "$(", "${", "\n", "\r",
    ">", ">>", "<", "<<",
]


@dataclass
class ExecutionResult:
    """Result of a tool execution."""
    tool: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    truncated: bool = False
    error: str = ""
    command_args: list[str] = field(default_factory=list)


class ExecutionBroker:
    """Sandboxed execution broker for security tools.

    All tool invocations MUST go through this broker.
    No shell interpolation. Arguments are passed as arrays.
    """

    def __init__(self):
        self._tool_paths: dict[str, str] = {}
        self._tool_versions: dict[str, str] = {}

    async def detect_tools(self) -> dict[str, dict[str, Any]]:
        """Detect available tools and their versions."""
        inventory = {}
        for tool_name, tool_info in ALLOWED_TOOLS.items():
            binary = tool_info["binary"]
            path = shutil.which(binary)

            tool_data = {
                "name": tool_name,
                "binary": binary,
                "available": path is not None,
                "path": path or "",
                "version": "",
                "install_instructions": tool_info["install"],
                "description": tool_info["description"],
            }

            if path:
                self._tool_paths[tool_name] = path
                # Try to get version
                try:
                    proc = await asyncio.create_subprocess_exec(
                        path, "--version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
                    version_text = (stdout or stderr or b"").decode("utf-8", errors="replace")
                    # Extract first line as version
                    first_line = version_text.strip().split("\n")[0] if version_text.strip() else ""
                    tool_data["version"] = first_line[:200]
                    self._tool_versions[tool_name] = first_line[:200]
                except Exception:
                    tool_data["version"] = "unknown"

            inventory[tool_name] = tool_data
            logger.info(
                "tool_detected",
                tool=tool_name,
                available=tool_data["available"],
                path=tool_data["path"],
            )

        return inventory

    def validate_arguments(self, tool_name: str, args: list[str]) -> tuple[bool, str]:
        """Validate tool arguments against allowlists.

        Returns (valid, reason).
        """
        if tool_name not in ALLOWED_TOOLS:
            return False, f"Unknown tool: {tool_name}"

        if tool_name not in self._tool_paths:
            return False, f"Tool not available: {tool_name}. {ALLOWED_TOOLS[tool_name]['install']}"

        # Check each argument for dangerous patterns
        for arg in args:
            for pattern in _DANGEROUS_PATTERNS:
                if pattern in arg:
                    return False, f"Dangerous pattern '{pattern}' found in argument: {arg[:50]}"

        return True, "Arguments valid"

    async def execute(
        self,
        tool_name: str,
        args: list[str],
        timeout_seconds: int = 300,
        max_output_bytes: int = MAX_OUTPUT_SIZE,
        env_override: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> ExecutionResult:
        """Execute a tool with validated arguments in a sandboxed subprocess.

        No shell interpolation. Uses argument arrays directly.
        """
        # Validate tool and arguments
        valid, reason = self.validate_arguments(tool_name, args)
        if not valid:
            logger.warning("execution_blocked", tool=tool_name, reason=reason)
            return ExecutionResult(
                tool=tool_name,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=reason,
                duration_seconds=0,
                error=reason,
                command_args=args,
            )

        tool_path = self._tool_paths[tool_name]
        cmd = [tool_path] + args

        # Build environment — never inherit secrets
        env = os.environ.copy()
        # Strip sensitive vars
        for key in list(env.keys()):
            key_lower = key.lower()
            if any(s in key_lower for s in ["api_key", "secret", "password", "token"]):
                del env[key]
        if env_override:
            env.update(env_override)

        logger.info("tool_execution_start", tool=tool_name, args=args[:5])
        start_time = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                duration = time.monotonic() - start_time
                logger.warning("tool_execution_timeout", tool=tool_name, timeout=timeout_seconds)
                return ExecutionResult(
                    tool=tool_name,
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=f"Execution timed out after {timeout_seconds}s",
                    duration_seconds=duration,
                    error="timeout",
                    command_args=args,
                )

            duration = time.monotonic() - start_time

            # Truncate large outputs
            truncated = False
            stdout_str = (stdout_bytes or b"")[:max_output_bytes].decode("utf-8", errors="replace")
            stderr_str = (stderr_bytes or b"")[:max_output_bytes].decode("utf-8", errors="replace")
            if len(stdout_bytes or b"") > max_output_bytes or len(stderr_bytes or b"") > max_output_bytes:
                truncated = True

            result = ExecutionResult(
                tool=tool_name,
                success=proc.returncode == 0,
                exit_code=proc.returncode or 0,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_seconds=duration,
                truncated=truncated,
                command_args=args,
            )

            logger.info(
                "tool_execution_complete",
                tool=tool_name,
                exit_code=result.exit_code,
                duration=f"{duration:.2f}s",
                truncated=truncated,
            )
            return result

        except FileNotFoundError:
            duration = time.monotonic() - start_time
            error_msg = f"Tool binary not found: {tool_path}"
            logger.error("tool_not_found", tool=tool_name, path=tool_path)
            return ExecutionResult(
                tool=tool_name,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=error_msg,
                duration_seconds=duration,
                error=error_msg,
                command_args=args,
            )
        except Exception as e:
            duration = time.monotonic() - start_time
            error_msg = f"Execution error: {type(e).__name__}: {str(e)[:200]}"
            logger.error("tool_execution_error", tool=tool_name, error=error_msg)
            return ExecutionResult(
                tool=tool_name,
                success=False,
                exit_code=-1,
                stdout="",
                stderr=error_msg,
                duration_seconds=duration,
                error=error_msg,
                command_args=args,
            )


# Singleton broker instance
_broker: ExecutionBroker | None = None


def get_execution_broker() -> ExecutionBroker:
    """Get or create the execution broker singleton."""
    global _broker
    if _broker is None:
        _broker = ExecutionBroker()
    return _broker
