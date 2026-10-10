"""SentinelWeb AI — Execution Broker tests.

Tests verify:
- Dangerous arguments are blocked
- Unknown tools are rejected
- Argument validation works correctly
"""

import pytest

from app.core.execution import ExecutionBroker


class TestArgumentValidation:
    """Test argument sanitization and validation."""

    def setup_method(self):
        self.broker = ExecutionBroker()
        # Simulate tool detection
        self.broker._tool_paths["curl"] = "/usr/bin/curl"

    def test_valid_arguments(self):
        valid, reason = self.broker.validate_arguments("curl", ["-s", "-I", "https://example.com"])
        assert valid is True

    def test_shell_injection_semicolon(self):
        valid, reason = self.broker.validate_arguments("curl", ["-s", "https://example.com; rm -rf /"])
        assert valid is False
        assert "Dangerous pattern" in reason

    def test_shell_injection_pipe(self):
        valid, reason = self.broker.validate_arguments("curl", ["https://example.com | cat /etc/passwd"])
        assert valid is False

    def test_shell_injection_backtick(self):
        valid, reason = self.broker.validate_arguments("curl", ["`whoami`"])
        assert valid is False

    def test_shell_injection_dollar_paren(self):
        valid, reason = self.broker.validate_arguments("curl", ["$(id)"])
        assert valid is False

    def test_shell_injection_ampersand(self):
        valid, reason = self.broker.validate_arguments("curl", ["https://example.com && evil"])
        assert valid is False

    def test_output_redirect_blocked(self):
        valid, reason = self.broker.validate_arguments("curl", ["-o", "> /etc/shadow"])
        assert valid is False

    def test_unknown_tool_blocked(self):
        valid, reason = self.broker.validate_arguments("evil_tool", ["--hack"])
        assert valid is False
        assert "Unknown tool" in reason

    def test_unavailable_tool_blocked(self):
        valid, reason = self.broker.validate_arguments("nmap", ["-sV", "example.com"])
        assert valid is False
        assert "not available" in reason


class TestToolDetection:
    """Test tool inventory detection."""

    @pytest.mark.asyncio
    async def test_detect_tools_returns_dict(self):
        broker = ExecutionBroker()
        inventory = await broker.detect_tools()
        assert isinstance(inventory, dict)
        assert "curl" in inventory
        assert "nmap" in inventory
        # Each tool should have required fields
        for name, data in inventory.items():
            assert "available" in data
            assert "path" in data
            assert "install_instructions" in data
